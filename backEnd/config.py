import os

# API Keys
GOOGLE_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# File paths
DB_FILE = "item_registry.json"
PANTRY_STATE_FILE = "pantry_state.json"
BOTS_FILE = "bots.json"

# Server settings
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
