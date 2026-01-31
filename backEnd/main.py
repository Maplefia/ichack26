from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import socket

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
    
@app.route('/api/recipes', methods=['POST'])
def recipe_handler():
    try:
        print('a')
        info = request.get_json()
        print(info['allergens'])
        return jsonify(info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/edit_inventory', methods=['POST'])
def edit_inv():
    try: 
        newstock = request.get_json()
        # we replace current_full_inventory with newstock
        json_path = os.path.join(os.path.dirname(__file__), 'pantry_state.json')
        with open(json_path, 'r') as file:
            pantry_data = json.load(file)
        pantry_data['current_full_inventory'] = newstock
        with open(json_path, 'w') as file:
            json.dump(pantry_data, file, indent=4)
        return jsonify({'message': 'Inventory updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/inventory', methods=['GET'])
def send_inv():
    try:
        # Get the path to pantry_state.json
        json_path = os.path.join(os.path.dirname(__file__), 'pantry_state.json')
        
        with open(json_path, 'r') as file:
            pantry_data = json.load(file)
        
        # Return only current_full_inventory
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
    print(f"  Local:   http://localhost:5000/api/bots")
    print(f"  Network: http://{local_ip}:5000/api/bots")
    print(f"{'='*50}\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
