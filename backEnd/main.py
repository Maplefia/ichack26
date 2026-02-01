from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import socket
import uuid
import datetime
from recipe_service import generate_recipes

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# UUID registry for consistent item IDs
PANTRY_STATE_FILE = os.path.join(os.path.dirname(__file__), 'pantry_state.json')

def get_or_create_uuid(item_name: str) -> str:
    """Generate or retrieve UUID for an item name to ensure consistency"""
    name_key = item_name.strip().lower()
    
    # Load pantry_state.json
    pantry_data = {}
    if os.path.exists(PANTRY_STATE_FILE):
        with open(PANTRY_STATE_FILE, "r") as f:
            pantry_data = json.load(f)
    
    # Get or create item_registry within pantry_state
    registry = pantry_data.get('item_registry', {})
    
    if name_key in registry:
        return registry[name_key]
    
    # Generate new UUID and save back to pantry_state
    new_id = str(uuid.uuid4())
    registry[name_key] = new_id
    pantry_data['item_registry'] = registry
    
    with open(PANTRY_STATE_FILE, "w") as f:
        json.dump(pantry_data, f, indent=4)
    
    return new_id

@app.route('/api/bots', methods=['GET'])
def get_bots():
    try:
        # Get the path to bots.json (assumes it's in the same directory)
        json_path = os.path.join(os.path.dirname(__file__), 'bots.json')
        
        with open(json_path, 'r') as file:
            bots_data = json.load(file)
        
        return jsonify(bots_data), 200
    except FileNotFoundError:
        return jsonify({'error': 'bots.json not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
def create_pantry_state_if_not_exists():
    if not os.path.exists(PANTRY_STATE_FILE):
        initial_pantry_data = {
            "item_registry": {},
            "items_added": [],
            "items_removed": [],
            "current_full_inventory": []
        }
        with open(PANTRY_STATE_FILE, "w") as f:
            json.dump(initial_pantry_data, f, indent=4)
        print(f"Created initial {PANTRY_STATE_FILE}")

    
@app.route('/api/recipes', methods=['POST'])
def recipe_handler():
    try:
        request_data = request.get_json()
        allergens = request_data.get('allergens', [])
        
        if not isinstance(allergens, list):
            return jsonify({'error': 'Allergens must be a list of strings'}), 400

        # Ensure pantry_state.json exists before attempting to read
        create_pantry_state_if_not_exists()

        pantry_data = {}
        with open(PANTRY_STATE_FILE, "r") as f:
            try:
                pantry_data = json.load(f)
            except json.JSONDecodeError:
                return jsonify({'error': 'Invalid JSON format in pantry_state.json'}), 500
        
        current_inventory_raw = pantry_data.get('current_full_inventory', [])
        
        # Extract only the names of the ingredients from the inventory objects
        pantry_ingredient_names = []
        for item in current_inventory_raw:
            if isinstance(item, dict) and "name" in item and item["name"].strip():
                pantry_ingredient_names.append(item["name"].strip())
        
        # Call the generate_recipes function from recipe_service.py
        # This function now returns a JSON string
        recipes_json_string = generate_recipes(
            pantry_ingredient_names=pantry_ingredient_names,
            allergies=allergens,
            llm_model_name="gemini-3-flash-preview" # Specify your desired LLM here
        )
        
        # Parse the JSON string from generate_recipes back into a Python dict
        # so Flask's jsonify can properly serialize it.
        recipes_data = json.loads(recipes_json_string)

        return jsonify(recipes_data), 200
    except ValueError as e:
        # Catch specific validation errors, e.g., if API key is not set
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Error in /api/recipes: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory', methods=['POST'])
def add_inventory_item():
    try: 
        new_item = request.get_json()
        json_path = os.path.join(os.path.dirname(__file__), 'pantry_state.json')
        
        with open(json_path, 'r') as file:
            pantry_data = json.load(file)
        current_inventory = pantry_data.get('current_full_inventory', [])
        
        # Generate UUID for the new item based on its name
        new_item['id'] = get_or_create_uuid(new_item['name'])
        new_item['date_added'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        current_inventory.append(new_item)
        pantry_data['current_full_inventory'] = current_inventory
        
        with open(json_path, 'w') as file:
            json.dump(pantry_data, file, indent=4)
        
        return jsonify(new_item), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory/<item_id>', methods=['DELETE'])
def delete_inventory_item(item_id):
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'pantry_state.json')
        
        with open(json_path, 'r') as file:
            pantry_data = json.load(file)
        
        current_inventory = pantry_data.get('current_full_inventory', [])
        updated_inventory = [item for item in current_inventory if item.get('id') != item_id]
        if len(updated_inventory) == len(current_inventory):
            return jsonify({'error': 'Item not found'}), 404
        pantry_data['current_full_inventory'] = updated_inventory
        
        with open(json_path, 'w') as file:
            json.dump(pantry_data, file, indent=4)
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'pantry_state.json')
        
        with open(json_path, 'r') as file:
            pantry_data = json.load(file)
        
        inventory = pantry_data.get('current_full_inventory', [])
        return jsonify(inventory), 200
    except FileNotFoundError:
        return jsonify({'error': 'pantry_state.json not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "Unable to get IP"

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"Server starting on:")
    print(f"  Local:   http://localhost:5001/api/bots")
    print(f"  Network: http://{local_ip}:5001/api/bots")
    print(f"{'='*50}\n")
    app.run(debug=True, host='0.0.0.0', port=5001)
