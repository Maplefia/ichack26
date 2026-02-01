from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import socket
import uuid
import datetime
from pantry_analyzer import analyze_pantry_images
import threading

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

PANTRY_STATE_FILE = os.path.join(os.path.dirname(__file__), 'pantry_state.json')

latest_frame = None
prev_capture = None
latest_capture = None

def get_or_create_uuid(item_name: str) -> str:
    """Generate or retrieve UUID for an item name to ensure consistency"""
    name_key = item_name.strip().lower()
    
    # Load pantry_state.json
    pantry_data = {}
    if os.path.exists(PANTRY_STATE_FILE):
        with open(PANTRY_STATE_FILE, "r") as f:
            try:
                pantry_data = json.load(f)
            except json.JSONDecodeError:
                pantry_data = {}
    
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

def analyze_pantry_thread(before_img, after_img):
    """
    Thread function to analyze pantry changes between before and after images
    """
    try:
        print("Starting pantry analysis...")
        
        # Run the analysis
        _ = analyze_pantry_images(before_img, after_img)
        
        print(f"Pantry analysis complete.")
        
    except Exception as e:
        print(f"Error in pantry analysis thread: {e}")

# region endpoints
@app.route('/api/bots', methods=['GET', 'POST'])
def handle_bots():
    json_path = os.path.join(os.path.dirname(__file__), 'bots.json')
    
    if request.method == 'GET':
        # Frontend requests bot status
        try:
            with open(json_path, 'r') as file:
                bots_data = json.load(file)
            return jsonify(bots_data), 200
        except FileNotFoundError:
            return jsonify({'error': 'bots.json not found'}), 404
        except json.JSONDecodeError:
            return jsonify({'error': 'Invalid JSON format'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'POST':
        # ESP32 bot posting status update
        try:
            bot_update = request.get_json()
            
            # Validate required fields
            if 'id' not in bot_update or 'status' not in bot_update:
                return jsonify({'error': 'Missing id or status field'}), 400
            
            bot_id = bot_update['id']
            
            # Load existing bots
            try:
                with open(json_path, 'r') as file:
                    bots_data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                bots_data = []
            
            # Find and update existing bot or add new one
            bot_found = False
            for i, bot in enumerate(bots_data):
                if bot.get('id') == bot_id:
                    # Update existing bot
                    bots_data[i] = bot_update
                    bot_found = True
                    break
            
            if not bot_found:
                # Add new bot
                bots_data.append(bot_update)
            
            # Save updated bots
            with open(json_path, 'w') as file:
                json.dump(bots_data, file, indent=4)
            
            print(f"Bot {bot_id} status updated: {bot_update.get('status')} | Battery: {bot_update.get('battery', 'N/A')}")
            return jsonify({'message': 'Bot status updated', 'bot': bot_update}), 200
            
        except Exception as e:
            print(f"Error updating bot status: {e}")
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

@app.route('/api/inventory', methods=['POST'])
def add_inventory_item():
    try: 
        new_item = request.get_json()
        
        with open(PANTRY_STATE_FILE, 'r') as file:
            pantry_data = json.load(file)
        current_inventory = pantry_data.get('current_full_inventory', [])
        
        # Generate UUID for the new item based on its name
        new_item['id'] = get_or_create_uuid(new_item['name'])
        new_item['date_added'] = datetime.datetime.now().strftime('%Y-%m-%d')
        
        current_inventory.append(new_item)
        pantry_data['current_full_inventory'] = current_inventory
        
        with open(PANTRY_STATE_FILE, 'w') as file:
            json.dump(pantry_data, file, indent=4)
        
        return jsonify(new_item), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
def delete_inventory_item(item_id):
    try:
        with open(PANTRY_STATE_FILE, 'r') as file:
            pantry_data = json.load(file)
        
        current_inventory = pantry_data.get('current_full_inventory', [])
        updated_inventory = [item for item in current_inventory if item.get('id') != item_id]
        if len(updated_inventory) == len(current_inventory):
            return jsonify({'error': 'Item not found'}), 404
        pantry_data['current_full_inventory'] = updated_inventory
        
        with open(PANTRY_STATE_FILE, 'w') as file:
            json.dump(pantry_data, file, indent=4)
        
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    try:
        with open(PANTRY_STATE_FILE, 'r') as file:
            pantry_data = json.load(file)
        
        inventory = pantry_data.get('current_full_inventory', [])
        return jsonify(inventory), 200
    except FileNotFoundError:
        return jsonify({'error': 'pantry_state.json not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON format'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route("/api/analyze_pantry", methods=["POST"])
def analyze_pantry():
    """
    Endpoint to analyze pantry changes from before/after images.
    Expects multipart/form-data with 'before_image' and 'after_image' files.
    """
    try:
        if "before_image" not in request.files or "after_image" not in request.files:
            return jsonify({"error": "Missing before_image or after_image"}), 400

        before_image = request.files["before_image"]
        after_image = request.files["after_image"]

        before_bytes = before_image.read()
        after_bytes = after_image.read()

        # Use the analyzer module
        response = analyze_pantry_images(before_bytes, after_bytes)

        return jsonify(response.dict()), 200

    except Exception as e:
        print(f"Error in analyze_pantry: {e}")
        return jsonify({"error": str(e)}), 500
    
# @app.route('/api/frame', methods=['POST'])
# def receive_frame():
#     """
#     ESP32 sends raw JPEG bytes here. We store them in a global variable.
#     """
#     global latest_frame
#     try:
#         # request.data contains the raw bytes (the image)
#         if request.data:
#             latest_frame = request.data
#             # print(f"Received frame: {len(latest_frame)} bytes") # Debug
#             return jsonify({'status': 'Frame updated'}), 200
#         else:
#             return jsonify({'error': 'No data received'}), 400
#     except Exception as e:
#         print(f"Error receiving frame: {e}")
#         return jsonify({'error': str(e)}), 500

# def generate_frames():
#     """
#     Generator function that yields the latest frame in MJPEG format.
#     """
#     while True:
#         if latest_frame: #latest_capture
#             # MJPEG format requires boundaries between frames
#             yield (b'--frame\r\n'
#                    b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')
        
#         # Sleep briefly to avoid 100% CPU usage loop
#         # The ESP32 sends frames every ~800ms, so 0.1s check is fine
#         time.sleep(0.1)

# @app.route('/video_feed')
# def video_feed():
#     """
#     The browser <img> tag will point here.
#     """
#     return Response(generate_frames(),
#                     mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/capture', methods=['POST'])
def receive_capture():
    """
    ESP32 sends raw JPEG bytes here. We store them in a global variable.
    """
    global prev_capture, latest_capture
    if not prev_capture:
        try:
            # request.data contains the raw bytes (the image)
            if request.data:
                prev_capture = request.data
                # print(f"Received capture: {len(prev_capture)} bytes")
                return jsonify({'status': 'Frame updated'}), 200
            else:
                return jsonify({'error': 'No data received'}), 400
        except Exception as e:
            print(f"Error receiving frame: {e}")
            return jsonify({'error': str(e)}), 500
    
    else:
        try:
            # request.data contains the raw bytes (the image)
            if request.data:
                latest_capture = request.data
                # print(f"Received frame: {len(latest_capture)} bytes")
                
                # Trigger analysis in separate thread (allows "queueing" multiple analyses)
                # We pass the current data as arguments so the thread has its own references
                thread = threading.Thread(target=analyze_pantry_thread, args=(prev_capture, latest_capture), daemon=True)
                thread.start()
                
                # Update captures immediately so we're ready for the next one
                prev_capture = latest_capture
                latest_capture = None
                
                return jsonify({'status': 'Frame updated, analysis started'}), 200
            else:
                return jsonify({'error': 'No data received'}), 400
        except Exception as e:
            print(f"Error receiving frame: {e}")
            return jsonify({'error': str(e)}), 500

@app.route('/view_stream')
def view_stream():
    """
    A simple HTML page to host the video feed.
    """
    html = """
    <html>
        <head>
            <title>Pantry Bot Live</title>
            <style>
                body { background-color: #222; color: white; text-align: center; font-family: sans-serif; }
                img { border: 2px solid #555; max-width: 100%; height: auto; }
            </style>
        </head>
        <body>
            <h1>Pantry Bot Live Stream</h1>
            <img src="/video_feed" />
        </body>
    </html>
    """
    return html

# endregion

# region server nom
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
    print(f"Available endpoints:")
    print(f"  GET  /api/bots")
    print(f"  POST /api/recipes")
    print(f"  GET  /api/inventory")
    print(f"  POST /api/inventory (Add Item)")
    print(f"  DEL  /api/inventory/<id> (Delete Item)")
    print(f"  POST /api/analyze_pantry")
    print(f"\nServer starting on:")
    print(f"  Local:   http://localhost:5001/api/bots")
    print(f"  Network: http://{local_ip}:5001/api/bots")
    print(f"{'='*50}\n")
    app.run(debug=True, host='0.0.0.0', port=5001)