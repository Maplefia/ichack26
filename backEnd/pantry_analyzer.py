import os
import base64
import json
import uuid
import datetime
from typing import List, Optional, cast
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from config import GOOGLE_API_KEY, DB_FILE, PANTRY_STATE_FILE

# Set environment variable
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# region pydantics
class PantryItem(BaseModel):
    id: str = Field(description="Unique UUID for the item")
    name: str = Field(description="The name of the food item")
    expiry_date: Optional[str] = Field(description="Estimated expiry date if available")

class LLMItemInput(BaseModel):
    name: str
    expiry_date: Optional[str]

class LLMPantryResponse(BaseModel):
    items_added: List[LLMItemInput] = Field(description="Items with name and expiry_date")
    items_removed: List[str] = Field(description="Names of items removed")
    current_full_inventory: List[LLMItemInput] = Field(description="List of all items in After image")

class PantryInventory(BaseModel):
    items_added: List[PantryItem]
    items_removed: List[PantryItem]
    current_full_inventory: List[PantryItem]
# endregion

# region db stuff
def get_or_create_uuid(item_name: str) -> str:
    """Get existing UUID for item or create new one"""
    name_key = item_name.strip().lower()
    registry = {}
    
    # Load existing pantry state which contains the registry
    pantry_data = {}
    if os.path.exists(PANTRY_STATE_FILE):
        try:
            with open(PANTRY_STATE_FILE, "r") as f:
                pantry_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            pantry_data = {}
    
    registry = pantry_data.get('item_registry', {})
    
    # Return existing ID if found
    if name_key in registry:
        return registry[name_key]
    
    # Create new ID and save immediately
    new_id = str(uuid.uuid4())
    registry[name_key] = new_id
    pantry_data['item_registry'] = registry # Update registry in data object

    # We save immediately to ensure consistency
    try:
        with open(PANTRY_STATE_FILE, "w") as f:
            json.dump(pantry_data, f, indent=4)
    except IOError as e:
        print(f"Warning: Could not save registry: {e}")
    
    return new_id
# endregion

# region helpers
def encode_image_bytes(image_bytes: bytes):
    """Encode image bytes to base64 string"""
    return base64.b64encode(image_bytes).decode("utf-8")

def map_to_pantry_item(item: LLMItemInput) -> PantryItem:
    """Convert LLM input to PantryItem with UUID"""
    return PantryItem(
        id=get_or_create_uuid(item.name),
        name=item.name,
        expiry_date=item.expiry_date
    )

def map_removed_string_to_item(name: str) -> PantryItem:
    """Convert removed item name to PantryItem with UUID"""
    return PantryItem(
        id=get_or_create_uuid(name),
        name=name,
        expiry_date=None
    )
# endregion

# region analysis
def analyze_pantry_images(before_bytes: bytes, after_bytes: bytes) -> PantryInventory:
    """
    Analyze before and after pantry images using Gemini AI.
    
    Args:
        before_bytes: Image bytes of pantry before changes
        after_bytes: Image bytes of pantry after changes
        
    Returns:
        PantryInventory object with added, removed, and current items
    """
    base64_before = encode_image_bytes(before_bytes)
    base64_after = encode_image_bytes(after_bytes)

    llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")
    structured_llm = llm.with_structured_output(LLMPantryResponse)

    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": f"""You are a pantry inventory specialist. Analyze the two images provided.
                Image 1 is the 'Before' state, and Image 2 is the 'After' state.
                Your task is to identify changes in food and grocery items only. Be as specific as possible with item names (e.g., "Heinz Tomato Ketchup" not "ketchup", "Olive Oil" not "oil"). Do not identify non-food items. If you cannot confidently identify an item, do not include it in the list. Do not express uncertainty.
                The current date is {current_date}. Use it to estimate a reasonable expiry date for any new items.

                Based on your analysis, provide the following information in the requested JSON format:
                1.  `items_added`: A list of all new food/grocery items present in the 'After' image but not the 'Before' image. Include your best estimate for the expiry date.
                2.  `items_removed`: A list of names of food/grocery items present in the 'Before' image but missing from the 'After' image.
                3.  `current_full_inventory`: A complete and clean list of every single food/grocery item visible in the 'After' image, along with estimated expiry dates.
                """
            },
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_before}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_after}"}}
        ]
    )

    raw_result = structured_llm.invoke([message])
    analysis = cast(LLMPantryResponse, raw_result)

    # Process with UUIDs
    processed_added = [map_to_pantry_item(i) for i in analysis.items_added]
    processed_full = [map_to_pantry_item(i) for i in analysis.current_full_inventory]
    processed_removed = [map_removed_string_to_item(name) for name in analysis.items_removed]

    response = PantryInventory(
        items_added=processed_added,
        items_removed=processed_removed,
        current_full_inventory=processed_full
    )

    # Load existing state to preserve item_registry
    existing_data = {}
    if os.path.exists(PANTRY_STATE_FILE):
         with open(PANTRY_STATE_FILE, "r") as f:
            try:
                existing_data = json.load(f)
            except:
                pass

    # Save to pantry state file, preserving registry
    pantry_state_payload = {
        "items_added": [i.dict() for i in processed_added],
        "items_removed": [i.name for i in processed_removed],
        "current_full_inventory": [i.dict() for i in processed_full],
        "item_registry": existing_data.get("item_registry", {})
    }
    
    with open(PANTRY_STATE_FILE, "w") as f:
        json.dump(pantry_state_payload, f, indent=4)

    return response
