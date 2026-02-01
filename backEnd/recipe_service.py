# recipe_service.py
import os
import json
from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

# --- Pydantic Models for Structured Output ---
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

def generate_recipes(
    pantry_ingredient_names: List[str], # Changed to accept a list of names directly
    allergies: List[str],
    llm_model_name: str = "gemini-3-flash-preview"
) -> str: # The function now explicitly returns a JSON string
    """
    Generates recipe names and ingredients based on pantry item names and allergies.

    Args:
        pantry_ingredient_names (List[str]): A list of ingredient names currently in the pantry.
        allergies (List[str]): A list of ingredients the person is allergic to.
        llm_model_name (str): The name of the LLM model to use (e.g., "gemini-1.5-flash").

    Returns:
        str: A JSON string containing the generated recipes. Returns an empty recipe list JSON string on error.
    """
    # Ensure GOOGLE_API_KEY is set
    if "GOOGLE_API_KEY" not in os.environ:
        raise ValueError("GOOGLE_API_KEY environment variable not set. Please set it before running the script.")

    # Clean and filter pantry ingredients (e.g., remove empty strings)
    cleaned_pantry_ingredients = [item.strip() for item in pantry_ingredient_names if item.strip()]

    if not cleaned_pantry_ingredients:
        print("No usable ingredients provided after cleaning. Cannot generate recipes.")
        return json.dumps({"recipes": []}) # Return empty JSON array for recipes

    # Initialize the LLM
    # Note: Model names like "gemini-3-flash-preview" might require specific access or updates.
    # Consider "gemini-1.5-flash" or "gemini-2.5-flash" if issues arise.
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
        "pantry_items": ", ".join(cleaned_pantry_ingredients), # Use the cleaned list of names
        "allergens": ", ".join(allergies) if allergies else "None",
        "format_instructions": parser.get_format_instructions(),
    }

    try:
        # Invoke the chain
        response = chain.invoke(input_data)
        # Return the Pydantic model dumped to a JSON string
        return response.model_dump_json(indent=2)
    except Exception as e:
        print(f"An error occurred during recipe generation: {e}")
        # Return an empty recipes list JSON string in case of error
        return json.dumps({"recipes": [], "error": str(e)})