from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import os
import re
import random
import requests
from datetime import datetime
import asyncio
import tempfile
import edge_tts
# from pydub import AudioSegment
# from pydub.playback import play

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

# --- CONFIG ---
# Using Groq API for real AI responses (free tier: https://console.groq.com)
# Get your free API key from: https://console.groq.com/keys
API_KEY = "gsk_REPLACE_WITH_YOUR_GROQ_API_KEY"  # Get free key from Groq console
API_PROVIDER = "groq"  # Options: "groq", "openrouter", "huggingface"
MODEL = "mixtral-8x7b-32768"  # Fast and capable Groq model (free tier)
VOICE = "en-US-GuyNeural"
HISTORY_FILE = "infini_think_chat_log.json"
MAX_HISTORY = 6

# Mock responses for when API is unavailable
MOCK_RESPONSES = [
    "Enna solraan da? 😎",
    "Dei, edhuku innum pesara? 🙄",
    "Infini Think here! That's interesting... 🔥",
    "Aah, interesting indeed! Tell me more 👀",
    "Haha, nice one! 😆",
]

# --- Load previous chat context ---
def load_context():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)[-MAX_HISTORY:]
                messages = []
                for item in data:
                    messages.append({"role": "user", "content": f"{item['user']} (from earlier)"})
                    messages.append({"role": "assistant", "content": f"{item['infini_think']} (your earlier reply)"})
                return messages
        except Exception as e:
            print("[WARNING] Failed to load chat history:", str(e))
    return []

# --- Save chat history to file ---
def save_to_json(user_text, venom_text):
    data = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
        except:
            pass
    data.append({
        "timestamp": str(datetime.now()),
        "user": user_text,
        "infini_think": venom_text
    })
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

# --- Get AI-generated reply from Groq or other providers ---
def get_infini_think_reply(prompt, context_messages):
    """Get response from AI API - Groq (recommended) or fallback."""
    
    if API_PROVIDER == "groq":
        return get_groq_reply(prompt, context_messages)
    else:
        return get_openrouter_reply(prompt, context_messages)

def get_groq_reply(prompt, context_messages):
    """Get response from Groq API (free, fast, and reliable)."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Build messages for Groq
    messages = [
        {
            "role": "system",
            "content": "You are 'Infini Think', a sarcastic multilingual Tamil-English AI assistant. Learn the user's tone and history. Speak with wit, sass, and roast. Keep replies concise and witty. Don't use asterisks for actions."
        },
        *context_messages,
        {"role": "user", "content": prompt}
    ]
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }
    
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            if result and isinstance(result, str):
                return result.strip()
        else:
            print(f"[ERROR] Groq API Error: {response.status_code}")
            if response.status_code == 401:
                print("[INFO] Invalid API key. Please update API_KEY in app.py")
    
    except Exception as e:
        print(f"[ERROR] Groq request failed: {str(e)}")
    
    return None

def get_openrouter_reply(prompt, context_messages):
    """Fallback to OpenRouter (if you have a valid key)."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    noise = f"(time: {datetime.now().strftime('%H:%M:%S')}, rand: {random.randint(1, 9999)})"
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are 'Infini Think', a sarcastic multilingual Tamil-English AI assistant. Learn the user's tone and history. Speak with wit, sass, and roast. Keep replies short and funny."
            },
            *context_messages,
            {"role": "user", "content": f"{prompt} {noise}"}
        ]
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()["choices"][0]["message"]["content"]
            if result and isinstance(result, str):
                return result.strip()
    
    except Exception as e:
        print(f"[ERROR] OpenRouter request failed: {str(e)}")
    
    return None

# --- Process a single query ---
def process_query(text):
    """Process a user query and return a safe response."""
    try:
        context = load_context()
        reply = get_infini_think_reply(text, context)
        
        # Ensure reply is never None or empty
        if not reply or not isinstance(reply, str):
            reply = random.choice(MOCK_RESPONSES)
        
        # Clean the reply safely
        try:
            cleaned_reply = re.sub(r"\*.*?\*", "", reply).strip()
        except (TypeError, AttributeError):
            cleaned_reply = reply
        
        # If cleaning removed everything, use original
        if not cleaned_reply:
            cleaned_reply = reply
        
        # Save to history
        save_to_json(text, reply)
        
        return cleaned_reply
    except Exception as e:
        print(f"[ERROR] process_query failed: {str(e)}")
        return random.choice(MOCK_RESPONSES)

# --- API Routes ---
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    try:
        data = request.get_json()
        if not data or not isinstance(data, dict):
            return jsonify({'error': 'Invalid JSON request', 'success': False}), 400
        
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty', 'success': False}), 400
        
        # Process the query
        reply = process_query(user_message)
        
        # Verify response is valid
        if not reply or not isinstance(reply, str):
            reply = random.choice(MOCK_RESPONSES)
        
        return jsonify({
            'reply': reply,
            'success': True
        }), 200
    
    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] Chat endpoint error: {error_msg}")
        return jsonify({
            'error': 'Server error processing your message',
            'success': False
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)
                return jsonify({'history': data, 'success': True}), 200
        return jsonify({'history': [], 'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    try:
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("[*] Infini Think API Server starting on http://localhost:5000...")
    app.run(debug=False, port=5000, host='0.0.0.0')