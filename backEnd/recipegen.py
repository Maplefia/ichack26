import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Configure the API key - Ensure you have this in your environment variables
os.environ["GOOGLE_API_KEY"] = os.environ.get("API_KEY", "")

llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview")

def generate_recipe(ingredients_prompt):
    """
    Sends a prompt to Gemini using LangChain and returns the generated recipe.
    """
    try:
        message = HumanMessage(
            content=f"Generate a recipe based on these ingredients: {ingredients_prompt}"
        )
        response = llm.invoke([message])
        return response.content
    except Exception as e:
        return f"An error occurred: {str(e)}"
