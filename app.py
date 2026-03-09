import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# ==========================================
# MongoDB Initialization
# ==========================================
# On Render, MONGO_URI should be set in the 'Environment' tab
MONGO_URI = os.environ.get("MONGO_URI")

try:
    if not MONGO_URI:
        print("❌ Error: MONGO_URI environment variable is missing!")
        print("Please add 'MONGO_URI' to your Render environment variables.")
        client = MongoClient('mongodb://localhost:27017/')
    elif "username" in MONGO_URI and "password" in MONGO_URI:
        print("⚠️ Warning: MONGO_URI still contains placeholder '<username>' or '<password>'!")
        client = MongoClient('mongodb://localhost:27017/')
    else:
        # Success - attempt connection
        client = MongoClient(MONGO_URI)
        client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!")
        
    db = client.life_os_db
    tasks_collection = db.tasks
    settings_collection = db.settings
    
except Exception as e:
    print(f"Failed to connect to MongoDB: {e}")


ai_client = None
ai_chat_session = None

# Initialize the AI if we already have the key saved in MongoDB
def auto_init_ai():
    try:
        key_doc = settings_collection.find_one({"_id": "gemini_api_key"})
        if key_doc and "value" in key_doc:
            init_ai(key_doc["value"], save_to_db=False)
    except Exception as e:
        print(f"Could not auto-init AI: {e}")

def init_ai(api_key, save_to_db=True):
    global ai_client, ai_chat_session
    try:
        ai_client = genai.Client(api_key=api_key)
        
        # Start the chat session with our custom prompt
        ai_chat_session = ai_client.chats.create(
            model="gemini-2.5-flash",
            config=dict(
                system_instruction="You are Nova, the personal AI assistant integrated into the user's Life OS application. Your goal is to help the user manage their tasks, answer questions, and be a friendly, helpful companion."
            )
        )
        
        # Save key to database permanently
        if save_to_db:
            settings_collection.update_one(
                {"_id": "gemini_api_key"},
                {"$set": {"value": api_key}},
                upsert=True
            )
            
        return True, "Success"
    except Exception as e:
        print(f"Failed to initialize AI: {e}")
        return False, str(e)


# ==========================================
# Frontend Routes
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')


# ==========================================
# API Routes: Tasks
# ==========================================
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    try:
        tasks = list(tasks_collection.find({}))
        # Convert ObjectId to string for JSON serialization
        for task in tasks:
            task['id'] = str(task['_id'])
            del task['_id']
        return jsonify(tasks)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
        
    try:
        new_task = {
            "title": data['title'],
            "completed": False
        }
        result = tasks_collection.insert_one(new_task)
        
        return jsonify({
            "id": str(result.inserted_id),
            "title": new_task['title'],
            "completed": False
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def update_task(task_id):
    data = request.json
    update_fields = {}
    
    if 'completed' in data:
        update_fields['completed'] = bool(data['completed'])
    if 'title' in data:
        update_fields['title'] = data['title']
        
    if not update_fields:
        return jsonify({"error": "No update fields provided"}), 400
        
    try:
        result = tasks_collection.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({"error": "Task not found"}), 404
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        result = tasks_collection.delete_one({"_id": ObjectId(task_id)})
        
        if result.deleted_count == 0:
            return jsonify({"error": "Task not found"}), 404
            
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# API Routes: AI Chatbot
# ==========================================
@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"ai_ready": ai_chat_session is not None})

@app.route('/api/chat', methods=['POST'])
def chat():
    global ai_chat_session
    data = request.json
    
    if not data:
        return jsonify({"error": "Invalid request"}), 400
        
    # Setup request
    if 'apiKey' in data:
        success, message = init_ai(data['apiKey'])
        if success:
            return jsonify({"success": True, "message": "API key saved and configured successfully!"})
        else:
            return jsonify({"success": False, "error": f"Failed to connect: {message}"}), 400
            
    # Message request
    if 'message' in data:
        if ai_chat_session is None:
            return jsonify({"error": "AI not initialized. Please provide an API key first."}), 401
            
        try:
            response = ai_chat_session.send_message(data['message'])
            return jsonify({"response": response.text})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    return jsonify({"error": "Missing 'message' or 'apiKey' field"}), 400


if __name__ == '__main__':
    auto_init_ai()
    # Use the PORT environment variable if available (for hosting)
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting MongoDB-Powered Life OS on port {port}...")
    app.run(debug=False, host='0.0.0.0', port=port)
