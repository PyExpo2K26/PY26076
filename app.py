from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import os
import re
import random
import requests
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
CORS(app)

# --- CONFIG ---
API_PROVIDER = "huggingface"
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
VOICE = "en-US-GuyNeural"
HISTORY_FILE = "infini_think_chat_log.json"
MAX_HISTORY = 6

# HuggingFace API Token
HF_TOKEN = "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"

# Mock responses for when API is unavailable
MOCK_RESPONSES = [
    "my brain is not braining right now",
    "Infini Think here! That's interesting... 🔥",
    "Aah, interesting indeed! Tell me more 👀",
    "Ok, I need to improve to satisfy your queries.",
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
            print(f"[WARNING] Failed to load chat history: {str(e)}")
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

# --- Get AI-generated reply using HuggingFace Inference Router ---
def get_free_inference_api(prompt, context_messages=None):
    """Use HuggingFace Inference Router with History Support."""
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
        "X-Wait-For-Model": "true" # Extra header for stability
    }
    
    # 1. Build the message list starting with system prompt
    messages = [{"role": "system", "content": "You are Infini Think, a helpful AI."}]
    
    # 2. Add historical context if it exists
    if context_messages:
        messages.extend(context_messages)
        
    # 3. Add the current user prompt
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300,
        "options": {"wait_for_model": True} # Critical for free tier
    }
    
    try:
        # Increased timeout to 60s because free models can be slow to wake up
        response = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60 
        )
        
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            print(f"[ERROR] API {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Request failed: {e}")
        return None
# --- Fallback API ---
def get_infini_think_reply(prompt, context_messages):
    # Pass the context into the API call now!
    reply = get_free_inference_api(prompt, context_messages)
    if reply:
        return reply
    
    # Fallback logic remains the same
    return get_alt_inference_api(prompt)
    
    payload = {
        "model": "HuggingFaceH4/zephyr-7b-beta",
        "messages": [
            {"role": "system", "content": "You are a helpful AI assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 250
    }
    
    try:
        response = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0].get("message", {}).get("content", "").strip()
                if text:
                    return text
        
        return None
    
    except Exception as e:
        print(f"[ERROR] Fallback API failed: {str(e)}")
        return None

# --- Get response from AI (with fallback) ---
def get_infini_think_reply(prompt, context_messages):
    """Get response from AI - tries primary API then fallback."""
    # Try primary API
    reply = get_free_inference_api(prompt)
    if reply:
        return reply
    
    # Try fallback API
    print("[INFO] Primary API failed, trying fallback...")
    reply = get_alt_inference_api(prompt)
    if reply:
        return reply
    
    print("[INFO] All APIs failed, returning mock response")
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
