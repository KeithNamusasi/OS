import os
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'life_os.db')

# ==========================================
# SQLite Database Initialization
# ==========================================
def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tasks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            category TEXT DEFAULT 'general',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            description TEXT DEFAULT '',
            created_at TEXT
        )
    ''')
    
    # Create notes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            color TEXT DEFAULT '#6366f1',
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # Create settings table (for storing API key)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("SQLite database initialized successfully!")

# Initialize database on startup
init_db()

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


ai_client = None
ai_chat_session = None

# Initialize the AI if we already have the key saved in database
def auto_init_ai():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("gemini_api_key",))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            init_ai(row[0], save_to_db=False)
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
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                          ("gemini_api_key", api_key))
            conn.commit()
            conn.close()
            
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks")
        tasks = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        tasks_list = []
        for task in tasks:
            tasks_list.append({
                "id": task["id"],
                "title": task["title"],
                "completed": bool(task["completed"]),
                "category": task["category"],
                "priority": task["priority"],
                "due_date": task["due_date"],
                "description": task["description"]
            })
        return jsonify(tasks_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.json
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (title, completed, category, priority, due_date, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['title'],
            0,
            data.get('category', 'general'),
            data.get('priority', 'medium'),
            data.get('due_date', None),
            data.get('description', ''),
            data.get('created_at', None)
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "id": task_id,
            "title": data['title'],
            "completed": False,
            "category": data.get('category', 'general'),
            "priority": data.get('priority', 'medium'),
            "due_date": data.get('due_date', None),
            "description": data.get('description', '')
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['PATCH'])
def update_task(task_id):
    data = request.json
    update_fields = []
    update_values = []
    
    if 'completed' in data:
        update_fields.append("completed = ?")
        update_values.append(1 if data['completed'] else 0)
    if 'title' in data:
        update_fields.append("title = ?")
        update_values.append(data['title'])
    if 'category' in data:
        update_fields.append("category = ?")
        update_values.append(data['category'])
    if 'priority' in data:
        update_fields.append("priority = ?")
        update_values.append(data['priority'])
    if 'due_date' in data:
        update_fields.append("due_date = ?")
        update_values.append(data['due_date'])
    if 'description' in data:
        update_fields.append("description = ?")
        update_values.append(data['description'])
        
    if not update_fields:
        return jsonify({"error": "No update fields provided"}), 400
        
    try:
        update_values.append(task_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?", update_values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Task not found"}), 404
            
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Task not found"}), 404
            
        conn.commit()
        conn.close()
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


# ==========================================
# API Routes: Notes
# ==========================================
@app.route('/api/notes', methods=['GET'])
def get_notes():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY id DESC")
        notes = cursor.fetchall()
        conn.close()
        
        notes_list = []
        for note in notes:
            notes_list.append({
                "id": note["id"],
                "title": note["title"],
                "content": note["content"],
                "color": note["color"]
            })
        return jsonify(notes_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes', methods=['POST'])
def create_note():
    data = request.json
    if not data or 'title' not in data:
        return jsonify({"error": "Title is required"}), 400
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notes (title, content, color, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['title'],
            data.get('content', ''),
            data.get('color', '#6366f1'),
            data.get('created_at', None),
            data.get('updated_at', None)
        ))
        
        note_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "id": note_id,
            "title": data['title'],
            "content": data.get('content', ''),
            "color": data.get('color', '#6366f1')
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes/<note_id>', methods=['PATCH'])
def update_note(note_id):
    data = request.json
    update_fields = []
    update_values = []
    
    if 'title' in data:
        update_fields.append("title = ?")
        update_values.append(data['title'])
    if 'content' in data:
        update_fields.append("content = ?")
        update_values.append(data['content'])
    if 'color' in data:
        update_fields.append("color = ?")
        update_values.append(data['color'])
        
    if not update_fields:
        return jsonify({"error": "No update fields provided"}), 400
        
    try:
        update_values.append(note_id)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE notes SET {', '.join(update_fields)} WHERE id = ?", update_values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Note not found"}), 404
            
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"error": "Note not found"}), 404
            
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# AI Task Creation from Natural Language
# ==========================================
@app.route('/api/ai/create-task', methods=['POST'])
def ai_create_task():
    global ai_chat_session
    data = request.json
    
    if not data or 'prompt' not in data:
        return jsonify({"error": "Prompt is required"}), 400
        
    if ai_chat_session is None:
        return jsonify({"error": "AI not initialized. Please provide an API key first."}), 401
    
    prompt = data['prompt']
    
    # Create a prompt to extract task details
    extraction_prompt = f"""Analyze this request and extract task details. Return ONLY a JSON object with these fields (no other text):
- title: short task title
- category: one of [general, work, personal, health, learning, shopping] (default: general)
- priority: one of [low, medium, high] (default: medium)
- due_date: ISO date string if mentioned (e.g., "2024-12-25"), otherwise null
- description: brief description if mentioned, otherwise empty string

Request: {prompt}

JSON:"""

    try:
        response = ai_chat_session.send_message(extraction_prompt)
        import json
        import re
        
        # Extract JSON from response
        text = response.text
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if json_match:
            task_data = json.loads(json_match.group())
            
            # Create the task in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tasks (title, completed, category, priority, due_date, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_data.get('title', prompt),
                0,
                task_data.get('category', 'general'),
                task_data.get('priority', 'medium'),
                task_data.get('due_date'),
                task_data.get('description', ''),
                data.get('created_at', None)
            ))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "task": {
                    "id": task_id,
                    "title": task_data.get('title', prompt),
                    "category": task_data.get('category', 'general'),
                    "priority": task_data.get('priority', 'medium'),
                    "due_date": task_data.get('due_date'),
                    "description": task_data.get('description', '')
                }
            })
        else:
            # Fallback: create simple task
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tasks (title, completed, category, priority, due_date, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (prompt, 0, 'general', 'medium', None, '', data.get('created_at', None)))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "task": {
                    "id": task_id,
                    "title": prompt,
                    "category": "general",
                    "priority": "medium"
                }
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    auto_init_ai()
    # Use the PORT environment variable if available (for hosting)
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Life OS on port {port}...")
    app.run(debug=True, host='0.0.0.0', port=port)
