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
import logging
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "DELETE", "OPTIONS"]}})

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIG ---
HISTORY_FILE = "infini_think_chat_log.json"
CONVERSATIONS_FILE = "conversations.json"
CREDENTIALS_FILE = "user_credentials.json"
MAX_HISTORY = 6
API_TIMEOUT = 30  # seconds

# Groq API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# HuggingFace API Configuration (fallback)
HF_TOKEN = os.getenv("HF_TOKEN", "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")
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
    """Hash password using SHA256. In production, use bcrypt."""
    if not password or not isinstance(password, str):
        raise ValueError("Invalid password")
    return hashlib.sha256(password.encode()).hexdigest()

# --- Sanitize input ---
def sanitize_input(text):
    """Remove potentially harmful characters from input"""
    if not isinstance(text, str):
        return ""
    # Remove control characters and limit length
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)
    return text[:500]  # Max 500 chars

# --- Rate limiting decorator ---
from time import time as get_time
request_times = {}

def rate_limit(limit_per_minute=30):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = get_time()
            
            if client_ip not in request_times:
                request_times[client_ip] = []
            
            # Clean old requests (older than 1 minute)
            request_times[client_ip] = [t for t in request_times[client_ip] if current_time - t < 60]
            
            if len(request_times[client_ip]) >= limit_per_minute:
                return jsonify({'error': 'Too many requests. Please try again later.', 'success': False}), 429
            
            request_times[client_ip].append(current_time)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

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
    try:
        # Sanitize inputs
        username = sanitize_input(username).strip()
        email = sanitize_input(email).strip()
        
        # Validate inputs
        if not username or not email or not password:
            return {'success': False, 'error': 'All fields are required!'}
        
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
        
        logger.info(f"User registered: {username}")
        return {'success': True, 'message': 'User registered successfully!'}
    
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return {'success': False, 'error': 'Registration failed. Please try again.'}

# --- Verify user login ---
def verify_user_login(username, password):
    try:
        # Sanitize input
        username = sanitize_input(username).strip()
        
        if not username or not password:
            return {'success': False, 'error': 'Username and password are required!'}
        
        credentials = load_all_credentials()
        
        for user in credentials:
            if user["username"].lower() == username.lower():
                # Check if user has a password field (handle legacy users)
                if "password" not in user:
                    # Legacy user without password - set one for future logins
                    user["password"] = hash_password(password)
                    user["last_login"] = str(datetime.now())
                    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                        json.dump(credentials, file, indent=2, ensure_ascii=False)
                    logger.info(f"Legacy user password set: {username}")
                    return {'success': True, 'username': user['username'], 'message': 'Welcome! Your password has been set.'}
                
                # Verify password
                if user["password"] == hash_password(password):
                    # Update last login
                    user["last_login"] = str(datetime.now())
                    with open(CREDENTIALS_FILE, "w", encoding="utf-8") as file:
                        json.dump(credentials, file, indent=2, ensure_ascii=False)
                    logger.info(f"User logged in: {username}")
                    return {'success': True, 'username': user['username']}
                else:
                    logger.warning(f"Failed login attempt: {username}")
                    return {'success': False, 'error': 'Invalid password!'}
        
        logger.warning(f"Login attempt with unknown username: {username}")
        return {'success': False, 'error': 'Username not found!'}
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return {'success': False, 'error': 'Login failed. Please try again.'}

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
    try:
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
        
        logger.info(f"[Groq] Calling API with model: {GROQ_MODEL}")
        response = requests.post(
            GROQ_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=API_TIMEOUT
        )
        
        logger.info(f"[Groq] Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0].get('message', {}).get('content', '').strip()
                if content:
                    logger.info(f"[Groq] Success: {content[:60]}...")
                    return content
                else:
                    logger.error("[Groq] Empty content received")
                    return None
            else:
                logger.error(f"[Groq] Unexpected response structure")
                return None
        else:
            logger.error(f"[Groq] API Error {response.status_code}: {response.text[:200]}")
            return None
            
    except requests.Timeout:
        logger.error("[Groq] Request timeout")
        return None
    except requests.ConnectionError:
        logger.error("[Groq] Connection error")
        return None
    except Exception as e:
        logger.error(f"[Groq] Error: {str(e)}")
        return None

# --- HuggingFace Text Generation API Call (Fallback) ---
def get_huggingface_response(prompt, context_messages):
    try:
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
        
        logger.info(f"[HuggingFace] Calling API with model: {HF_MODEL}")
        response = requests.post(
            f"{HF_ENDPOINT}/{HF_MODEL}",
            headers=headers,
            json=payload,
            timeout=API_TIMEOUT
        )
        
        logger.info(f"[HuggingFace] Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                content = result[0].get('generated_text', '').strip()
                # Extract just the response part (after "Assistant:")
                if "Assistant:" in content:
                    content = content.split("Assistant:")[-1].strip()
                if content:
                    logger.info(f"[HuggingFace] Success: {content[:60]}...")
                    return content
                else:
                    logger.error("[HuggingFace] Empty content")
                    return None
            else:
                logger.error(f"[HuggingFace] Unexpected response")
                return None
        else:
            logger.error(f"[HuggingFace] API Error {response.status_code}")
            return None
            
    except requests.Timeout:
        logger.error("[HuggingFace] Request timeout")
        return None
    except requests.ConnectionError:
        logger.error("[HuggingFace] Connection error")
        return None
    except Exception as e:
        logger.error(f"[HuggingFace] Error: {str(e)}")
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
            logger.warning("Using mock response due to API failure")
        
        # Clean up any AI-style thought marks like *thinking*
        cleaned_reply = re.sub(r"\*.*?\*", "", reply).strip()
        
        if not cleaned_reply:
            cleaned_reply = random.choice(MOCK_RESPONSES)
        
        # Save this interaction
        save_to_json(text, cleaned_reply)
        return cleaned_reply
        
    except Exception as e:
        logger.error(f"process_query error: {e}")
        return random.choice(MOCK_RESPONSES)

# --- Routes ---
@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/console')
def console():
    return render_template('console.html')

@app.route('/api/chat', methods=['POST'])
@rate_limit(limit_per_minute=30)
def chat():
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided', 'success': False}), 400
            
        user_message = sanitize_input(data.get('message', '')).strip()
        conversation_id = data.get('conversation_id', 'default')
        
        if not user_message:
            return jsonify({'error': 'Message cannot be empty', 'success': False}), 400
        
        reply = process_query(user_message)
        
        # Store message in conversation
        add_message_to_conversation(conversation_id, user_message, reply)
        
        return jsonify({'reply': reply, 'conversation_id': conversation_id, 'success': True})
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({'error': 'Failed to process message', 'success': False}), 500

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
@rate_limit(limit_per_minute=5)
def api_register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'success': False}), 400
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required', 'success': False}), 400
        
        result = register_user(username, email, password)
        return jsonify(result), (200 if result['success'] else 400)
    except Exception as e:
        logger.error(f"Register endpoint error: {str(e)}")
        return jsonify({'error': 'Server error. Please try again.', 'success': False}), 500

@app.route('/api/login', methods=['POST'])
@rate_limit(limit_per_minute=10)
def api_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request', 'success': False}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required', 'success': False}), 400
        
        result = verify_user_login(username, password)
        return jsonify(result), (200 if result['success'] else 401)
    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}")
        return jsonify({'error': 'Server error. Please try again.', 'success': False}), 500

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
    logger.info("🔥 Starting Infini Think Flask App")
    logger.info(f"Primary API: {GROQ_MODEL}")
    logger.info(f"Fallback API: {HF_MODEL}")
    logger.info("Server running on http://0.0.0.0:5000")
    # Using debug=True is helpful during development
    app.run(debug=True, port=5000, host="0.0.0.0")
