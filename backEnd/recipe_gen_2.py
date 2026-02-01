import json
import os
from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

# --- 1. Define Pydantic Models for Structured Output ---
class RecipeIngredient(BaseModel):
    """Represents a single ingredient in a recipe."""
    name: str = Field(description="The name of the ingredient.")

class Recipe(BaseModel):
    """Represents a single recipe with its name and ingredients."""
    name: str = Field(description="The name of the recipe.")
    ingredients: List[str] = Field(description="A list of key ingredients for the recipe. Do not include basic items like salt, pepper, or water unless they are central to the recipe.")

class RecipeList(BaseModel):
    """Represents a list of generated recipes."""
    recipes: List[Recipe] = Field(description="A list of 5 recipe suggestions.")

# --- 2. Load Pantry Ingredients ---
def load_pantry_ingredients(file_path: str) -> List[str]:
    """Loads pantry ingredients from a JSON file with the new structure."""
    try:
        with open(file_path, 'r') as f:
            pantry_data = json.load(f)
            
            # Check if 'current_full_inventory' key exists and is a list
            if "current_full_inventory" not in pantry_data or not isinstance(pantry_data["current_full_inventory"], list):
                raise ValueError("Pantry JSON file must contain a 'current_full_inventory' list.")
            
            # Extract names from the inventory
            ingredients = []
            for item in pantry_data["current_full_inventory"]:
                if isinstance(item, dict) and "name" in item:
                    # Basic cleaning: remove empty strings and leading/trailing whitespace
                    if item["name"].strip():
                        ingredients.append(item["name"].strip())
                else:
                    print(f"Warning: Skipping malformed item in inventory: {item}")
            return ingredients
            
    except FileNotFoundError:
        print(f"Error: Pantry file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {file_path}")
        return []
    except ValueError as e:
        print(f"Error: {e}")
        return []

# --- 3. Main Recipe Generation Function ---
def generate_recipes(
    pantry_file: str,
    allergies: List[str],
    llm_model_name: str = "gemini-3-flash-preview"
) -> Dict:
    """
    Generates recipe names and ingredients based on pantry items and allergies.

    Args:
        pantry_file (str): Path to the JSON file containing current pantry ingredients.
        allergies (List[str]): A list of ingredients the person is allergic to.
        llm_model_name (str): The name of the LLM model to use (e.g., "gemini-1.5-flash").

    Returns:
        Dict: A dictionary containing the generated recipes in the specified JSON format.
    """
    # Ensure GOOGLE_API_KEY is set
    if "GOOGLE_API_KEY" not in os.environ:
        raise ValueError("GOOGLE_API_KEY environment variable not set. Please set it before running the script.")

    pantry_ingredients = load_pantry_ingredients(pantry_file)
    if not pantry_ingredients:
        print("No usable ingredients found in pantry. Cannot generate recipes.")
        return {"recipes": []}
    
    # --- IMPORTANT NOTE ON PANTRY CONTENTS ---
    # With your current pantry_stock.json containing mostly snacks and drinks,
    # the LLM will generate creative combinations or serving suggestions,
    # rather than traditional cooking recipes.
    # If you intend to generate traditional cooking recipes, please stock
    # your pantry with more fundamental cooking ingredients (e.g., vegetables, meats, grains, spices).
    print("\nNote: Your current pantry contains mostly snack items and drinks. "
          "The generated 'recipes' will reflect this, offering creative combinations "
          "or serving suggestions rather than traditional meal recipes.")

    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(model=llm_model_name, temperature=0.7)

    # Set up the parser for the structured output
    parser = PydanticOutputParser(pydantic_object=RecipeList)

    # Define the prompt template
    prompt_template = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert culinary assistant. "
                "Your task is to suggest 5 unique and creative recipe names along with their key ingredients. "
                "Prioritize using the provided pantry ingredients. "
                "Strictly avoid any ingredients that the user is allergic to. "
                "Ensure the recipes are actionable with the available pantry items, but you can suggest a few common additions. "
                "Output the recipes in a JSON format that matches the following schema:\n{format_instructions}"
            ),
            (
                "human",
                "Pantry ingredients: {pantry_items}\n"
                "Allergies to avoid: {allergens}\n"
                "Please provide 5 recipe suggestions."
            ),
        ]
    )

    # Create the LangChain chain
    chain = prompt_template | llm | parser

    # Prepare input for the chain
    input_data = {
        "pantry_items": ", ".join(pantry_ingredients), # Use all extracted ingredients
        "allergens": ", ".join(allergies) if allergies else "None",
        "format_instructions": parser.get_format_instructions(),
    }

    try:
        # Invoke the chain
        response = chain.invoke(input_data)
        return response.model_dump_json(indent=2)
    except Exception as e:
        print(f"An error occurred during recipe generation: {e}")
        return {"recipes": []}

