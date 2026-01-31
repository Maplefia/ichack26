import os
import base64
import json
import uuid
import datetime
from typing import List, Optional, cast
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# --- CONFIGURATION ---
os.environ["GOOGLE_API_KEY"] = "AIzaSyCjIeJ30-z7hpqjuvQts9_3vnI9v0KE4Uo"
DB_FILE = "item_registry.json"

app = FastAPI(title="Pantry Tracker API")

# --- MODELS ---

class PantryItem(BaseModel):
    id: str = Field(description="Unique UUID for the item")
    name: str = Field(description="The name of the food item")
    expiry_date: Optional[str] = Field(description="Estimated expiry date if available")

# Model for the LLM to fill out
class LLMItemInput(BaseModel):
    name: str
    expiry_date: Optional[str]

class LLMPantryResponse(BaseModel):
    items_added: List[LLMItemInput] = Field(description="Items with name and expiry_date")
    items_removed: List[str] = Field(description="Names of items removed")
    current_full_inventory: List[LLMItemInput] = Field(description="List of all items in After image")

class PantryInventory(BaseModel):
    items_added: List[PantryItem]
    items_removed: List[PantryItem] # Changed from List[str] to List[PantryItem]
    current_full_inventory: List[PantryItem]

# --- DATABASE LOGIC ---

def get_or_create_uuid(item_name: str) -> str:
    name_key = item_name.strip().lower()
    registry = {}
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            registry = json.load(f)
    
    if name_key in registry:
        return registry[name_key]
    
    new_id = str(uuid.uuid4())
    registry[name_key] = new_id
    with open(DB_FILE, "w") as f:
        json.dump(registry, f, indent=4)
    return new_id

# --- HELPER FUNCTIONS ---

def encode_image_bytes(image_bytes: bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

# --- API ENDPOINT ---

@app.post("/analyze-pantry", response_model=PantryInventory)
async def analyze_pantry(
    before_image: UploadFile = File(...), 
    after_image: UploadFile = File(...)
):
    try:
        before_bytes = await before_image.read()
        after_bytes = await after_image.read()
        
        base64_before = encode_image_bytes(before_bytes)
        base64_after = encode_image_bytes(after_bytes)

        llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview") # Use stable flash model
        structured_llm = llm.with_structured_output(LLMPantryResponse)

        current_date = datetime.datetime.now().strftime("%Y-%m-%d")

        message = HumanMessage(
            content=[
                {
                    "type": "text", 
                    "text": f"""Compare these two images of a pantry. 
                    Image 1: 'Before' state. Image 2: 'After' state.
                    Current Date: {current_date}.
                    Identify:
                    1. Specific items added in 'After' (with estimated expiry).
                    2. Items removed from 'Before'.
                    3. Clean list of EVERY item in 'After'.
                    """
                },
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_before}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_after}"}}
            ]
        )

        raw_result = structured_llm.invoke([message])
        analysis = cast(LLMPantryResponse, raw_result)

        # 5. PROCESS IDS (The Stability Layer)
        
        # Helper to convert LLM input objects to PantryItem with IDs
        def map_to_pantry_item(item: LLMItemInput):
            return PantryItem(
                id=get_or_create_uuid(item.name),
                name=item.name,
                expiry_date=item.expiry_date
            )

        # New helper to convert the "removed" strings to PantryItem with IDs
        def map_removed_string_to_item(name: str):
            return PantryItem(
                id=get_or_create_uuid(name),
                name=name,
                expiry_date=None # We don't need expiry for items no longer there
            )

        processed_added = [map_to_pantry_item(i) for i in analysis.items_added]
        processed_full = [map_to_pantry_item(i) for i in analysis.current_full_inventory]
        
        # This now creates objects with IDs for the removed items
        processed_removed = [map_removed_string_to_item(name) for name in analysis.items_removed]

        return PantryInventory(
            items_added=processed_added,
            items_removed=processed_removed,
            current_full_inventory=processed_full
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
