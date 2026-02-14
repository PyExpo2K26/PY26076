from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import os
import re
import random
import requests
from datetime import datetime
import uuid
import hashlib

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

# --- CONFIG ---
HISTORY_FILE = "infini_think_chat_log.json"
CONVERSATIONS_FILE = "conversations.json"
CREDENTIALS_FILE = "user_credentials.json"
MAX_HISTORY = 6

# Groq API Configuration
GROQ_API_KEY = "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"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# HuggingFace API Configuration (fallback)
HF_TOKEN = "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"
HF_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"
HF_ENDPOINT = "https://api-inference.huggingface.co/models"

MOCK_RESPONSES = [
    "My brain is not braining right now. 🧠",
    "Infini Think here! That's interesting... 🔥",
    "Aah, interesting indeed! Tell me more 👀",
    "Ok, I need to improve to satisfy your queries.",
]

# --- Load previous chat context ---
def load_context():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                # Take last few messages for context
                recent_data = data[-MAX_HISTORY:]
                messages = []
                for item in recent_data:
                    messages.append({"role": "user", "content": item.get('user', '')})
                    messages.append({"role": "assistant", "content": item.get('infini_think', '')})
                return messages
        except Exception as e:
            print(f"[WARNING] Failed to load chat history: {str(e)}")
    return []

# --- Save chat history ---
def save_to_json(user_text, reply_text):
    data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except: pass
    data.append({
        "timestamp": str(datetime.now()), 
        "user": user_text, 
        "infini_think": reply_text
    })
    # Keep file size manageable
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data[-50:], file, indent=2, ensure_ascii=False)

# --- Migrate legacy users (convert users without passwords) ---
def migrate_legacy_users():
    """Convert legacy users without passwords to use default password"""
    try:
        credentials = load_all_credentials()
        updated = False
        for user in credentials:
            if "password" not in user:
                # Set a temporary default password for migration
                user["password"] = hash_password("default123")  # User should update on first login
                updated = True
        
        if updated:
            with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                json.dump(credentials, file, indent=2, ensure_ascii=False)
            print("[INFO] Legacy users migrated successfully")
    except Exception as e:
        print(f"[WARNING] Failed to migrate legacy users: {e}")

# --- Load all credentials ---
def load_all_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except: pass
    return []

# --- Hash password ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Check if user exists ---
def user_exists(username):
    credentials = load_all_credentials()
    return any(c["username"].lower() == username.lower() for c in credentials)

# --- Check if email exists ---
def email_exists(email):
    credentials = load_all_credentials()
    return any(c["email"].lower() == email.lower() for c in credentials)

# --- Validate email format ---
def is_valid_email(email):
    if not email or len(email.strip()) == 0:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email.strip(), re.IGNORECASE) is not None

# --- Register new user ---
def register_user(username, email, password):
    # Validate inputs
    if not username or not email or not password:
        return {'success': False, 'error': 'All fields are required!'}
    
    username = username.strip()
    email = email.strip()
    
    if len(username) < 3:
        return {'success': False, 'error': 'Username must be at least 3 characters!'}
    
    if len(password) < 6:
        return {'success': False, 'error': 'Password must be at least 6 characters!'}
    
    if not is_valid_email(email):
        return {'success': False, 'error': 'Invalid email address!'}
    
    if user_exists(username):
        return {'success': False, 'error': 'Username already taken!'}
    
    if email_exists(email):
        return {'success': False, 'error': 'Email already registered!'}
    
    credentials = load_all_credentials()
    credentials.append({
        "username": username,
        "email": email,
        "password": hash_password(password),
        "created_at": str(datetime.now()),
        "last_login": str(datetime.now())
    })
    
    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
        json.dump(credentials, file, indent=2, ensure_ascii=False)
    
    return {'success': True, 'message': 'User registered successfully!'}

# --- Verify user login ---
def verify_user_login(username, password):
    credentials = load_all_credentials()
    
    for user in credentials:
        if user["username"].lower() == username.lower():
            # Check if user has a password field (handle legacy users)
            if "password" not in user:
                # Legacy user without password - set one for future logins
                user["password"] = hash_password(password)
                with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                    json.dump(credentials, file, indent=2, ensure_ascii=False)
                # Allow login for legacy users
                user["last_login"] = str(datetime.now())
                with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                    json.dump(credentials, file, indent=2, ensure_ascii=False)
                return {'success': True, 'username': user['username'], 'message': 'Welcome! Your password has been set.'}
            
            if user["password"] == hash_password(password):
                # Update last login
                user["last_login"] = str(datetime.now())
                with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                    json.dump(credentials, file, indent=2, ensure_ascii=False)
                return {'success': True, 'username': user['username']}
            else:
                return {'success': False, 'error': 'Invalid password!'}
    
    return {'success': False, 'error': 'Username not found!'}

# --- Manage Conversations (Separate Chat Sessions) ---
def load_all_conversations():
    if os.path.exists(CONVERSATIONS_FILE):
        try:
            with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except: pass
    return []

def save_conversation(conversation_id, title, messages):
    conversations = load_all_conversations()
    
    # Check if conversation exists
    existing = [c for c in conversations if c["id"] == conversation_id]
    if existing:
        existing[0]["title"] = title
        existing[0]["messages"] = messages
        existing[0]["updated_at"] = str(datetime.now())
    else:
        conversations.append({
            "id": conversation_id,
            "title": title,
            "messages": messages,
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now())
        })
    
    with open(CONVERSATIONS_FILE, "w", encoding="utf-8") as file:
        json.dump(conversations, file, indent=2, ensure_ascii=False)

def get_conversation(conversation_id):
    conversations = load_all_conversations()
    for conv in conversations:
        if conv["id"] == conversation_id:
            return conv
    return None

def add_message_to_conversation(conversation_id, user_msg, ai_msg):
    conversation = get_conversation(conversation_id)
    if conversation:
        conversation["messages"].append({
            "timestamp": str(datetime.now()),
            "user": user_msg,
            "ai": ai_msg
        })
        save_conversation(conversation_id, conversation["title"], conversation["messages"])
    else:
        # Create new conversation with first message
        title = user_msg[:50] if len(user_msg) > 50 else user_msg
        save_conversation(conversation_id, title, [{
            "timestamp": str(datetime.now()),
            "user": user_msg,
            "ai": ai_msg
        }])

# --- Groq API Call ---
def get_groq_response(prompt, context_messages):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    messages = [{"role": "system", "content": "You are Infini Think, a witty and helpful AI assistant. Keep responses concise and friendly. Max 100 words."}]
    if context_messages:
        messages.extend(context_messages)
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300,
        "stream": False
    }
    
    try:
        print(f"[DEBUG] Calling Groq API with model: {GROQ_MODEL}")
        response = requests.post(
            GROQ_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"[DEBUG] Groq API Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0].get('message', {}).get('content', '').strip()
                if content:
                    print(f"[DEBUG] Got Groq response: {content[:80]}...")
                    return content
                else:
                    print("[ERROR] Empty content in Groq response")
                    return None
            else:
                print(f"[ERROR] Unexpected Groq response structure: {result}")
                return None
        else:
            print(f"[ERROR] Groq API Error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Groq connection failed: {e}")
        return None

# --- HuggingFace Text Generation API Call (Fallback) ---
def get_huggingface_response(prompt, context_messages):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Build context string for text-generation model
    context_text = ""
    if context_messages:
        for msg in context_messages[-2:]:  # Last 2 messages
            if msg.get('role') == 'user':
                context_text += f"User: {msg.get('content', '')}\n"
            else:
                context_text += f"Assistant: {msg.get('content', '')}\n"
    
    full_prompt = f"""You are Infini Think, a witty AI assistant. Keep response under 100 words.
{context_text}User: {prompt}
Assistant:"""
    
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.7,
        }
    }
    
    try:
        print(f"[DEBUG] Calling HuggingFace API with model: {HF_MODEL}")
        response = requests.post(
            f"{HF_ENDPOINT}/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        print(f"[DEBUG] HuggingFace API Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get('generated_text', '').strip()
                # Extract just the response part (after "Assistant:")
                if "Assistant:" in content:
                    content = content.split("Assistant:")[-1].strip()
                if content:
                    print(f"[DEBUG] Got HuggingFace response: {content[:80]}...")
                    return content
                else:
                    print("[ERROR] Empty content in HuggingFace response")
                    return None
            else:
                print(f"[ERROR] Unexpected HuggingFace response structure: {result}")
                return None
        else:
            print(f"[ERROR] HuggingFace API Error {response.status_code}: {response.text[:200]}")
            return None
            
    except Exception as e:
        print(f"[ERROR] HuggingFace connection failed: {e}")
        return None

# --- Primary API Call with Fallback ---
def get_infini_think_reply(prompt, context_messages):
    # Try Groq first
    reply = get_groq_response(prompt, context_messages)
    if reply:
        return reply
    
    # Fall back to HuggingFace
    print("[DEBUG] Groq API failed, trying HuggingFace...")
    reply = get_huggingface_response(prompt, context_messages)
    if reply:
        return reply
    
    # If both fail, return None so process_query uses mock response
    print("[DEBUG] Both APIs failed, using mock response")
    return None

def process_query(text):
    try:
        context = load_context()
        reply = get_infini_think_reply(text, context)
        
        # If the API gave nothing, use a backup
        if not reply:
            reply = random.choice(MOCK_RESPONSES)
        
        # Clean up any AI-style thought marks like *thinking*
        cleaned_reply = re.sub(r"\*.*?\*", "", reply).strip()
        
        # Save this interaction
        save_to_json(text, cleaned_reply)
        return cleaned_reply
        
    except Exception as e:
        print(f"[ERROR] process_query failed: {e}")
        return random.choice(MOCK_RESPONSES)

# --- Routes ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/console')
def console():
    return render_template('console.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided', 'success': False}), 400
        
    user_message = data.get('message', '').strip()
    conversation_id = data.get('conversation_id', 'default')
    
    reply = process_query(user_message)
    
    # Store message in conversation
    add_message_to_conversation(conversation_id, user_message, reply)
    
    return jsonify({'reply': reply, 'conversation_id': conversation_id, 'success': True})

@app.route('/api/console/status', methods=['GET'])
def console_status():
    try:
        history_exists = os.path.exists(HISTORY_FILE)
        history_size = 0
        message_count = 0
        
        if history_exists:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                message_count = len(data)
                history_size = os.path.getsize(HISTORY_FILE)
        
        return jsonify({
            'status': 'running',
            'model': f"{GROQ_MODEL} (Groq) + {HF_MODEL} (HuggingFace fallback)",
            'primary_api': 'Groq',
            'fallback_api': 'HuggingFace',
            'history_file': HISTORY_FILE,
            'history_exists': history_exists,
            'message_count': message_count,
            'history_size_kb': round(history_size / 1024, 2),
            'max_history_context': MAX_HISTORY,
            'success': True
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e), 'success': False}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return jsonify({'history': [], 'success': True})
        
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Transform response format to match frontend expectations
            history = [{'user': item['user'], 'venom': item['infini_think']} for item in data]
            return jsonify({'history': history, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            return jsonify({'message': 'Chat history cleared', 'success': True})
        else:
            return jsonify({'message': 'No history file to clear', 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/console/history', methods=['GET'])
def console_history():
    try:
        if not os.path.exists(HISTORY_FILE):
            return jsonify({'messages': [], 'count': 0, 'success': True})
        
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return jsonify({'messages': data, 'count': len(data), 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/console/clear', methods=['POST'])
def console_clear():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
            return jsonify({'message': 'Chat history cleared', 'success': True})
        else:
            return jsonify({'message': 'No history file to clear', 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/save-credentials', methods=['POST'])
def check_user():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({'error': 'Username required', 'success': False}), 400
        
        exists = user_exists(username)
        return jsonify({'exists': exists, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/get-credentials', methods=['GET'])
def get_user_credentials():
    try:
        credentials = load_all_credentials()
        return jsonify({'credentials': credentials, 'count': len(credentials), 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required', 'success': False}), 400
        
        result = register_user(username, email, password)
        return jsonify(result), (200 if result['success'] else 400)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required', 'success': False}), 400
        
        result = verify_user_login(username, password)
        return jsonify(result), (200 if result['success'] else 401)
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    try:
        conversations = load_all_conversations()
        # Return only metadata, not full messages
        result = [{'id': c['id'], 'title': c['title'], 'created_at': c['created_at'], 'updated_at': c['updated_at']} for c in conversations]
        return jsonify({'conversations': result, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
def get_conversation_detail(conversation_id):
    try:
        conversation = get_conversation(conversation_id)
        if conversation:
            return jsonify({'conversation': conversation, 'success': True})
        else:
            return jsonify({'error': 'Conversation not found', 'success': False}), 404
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/conversation', methods=['POST'])
def create_conversation():
    try:
        data = request.get_json()
        title = data.get('title', 'New Chat')
        conversation_id = str(uuid.uuid4())
        
        save_conversation(conversation_id, title, [])
        return jsonify({'conversation_id': conversation_id, 'title': title, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

@app.route('/api/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    try:
        conversations = load_all_conversations()
        conversations = [c for c in conversations if c['id'] != conversation_id]
        
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(conversations, f, indent=2, ensure_ascii=False)
        
        return jsonify({'message': 'Conversation deleted', 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'success': False}), 500

if __name__ == '__main__':
    # Migrate legacy users without passwords
    migrate_legacy_users()
    # Using debug=True is helpful during development
    app.run(debug=True, port=5000,host ="0.0.0.0")
