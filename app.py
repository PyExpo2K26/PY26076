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
# Using free inference APIs (no API key needed)
API_PROVIDER = "huggingface"  # Free inference API
MODEL = "facebook/blenderbot-400M-distill"
VOICE = "en-US-GuyNeural"
HISTORY_FILE = "infini_think_chat_log.json"
MAX_HISTORY = 6

# Mock responses for when API is unavailable
MOCK_RESPONSES = [
    "my brain is not braining right now",
    "Infini Think here! That's interesting... 🔥",
    "Aah, interesting indeed! Tell me more 👀",
    "Ok,I need to improve to ssatisfy your queries.",
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
    """Get response from free AI APIs - no key needed."""
    # Try primary API
    reply = get_free_inference_api(prompt)
    if reply:
        return reply
    
    # Fallback to alternative service
    print("[INFO] Primary API failed, trying alternative...")
    reply = get_alt_inference_api(prompt)
    if reply:
        return reply
    
    # Final fallback
    print("[INFO] APIs failed, returning mock response")
    return None

def get_free_inference_api(prompt):
    """Use HuggingFace free inference API - BlenderBot."""
    try:
        payload = {"inputs": prompt}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(
            "https://api-inference.huggingface.co/models/facebook/blenderbot-400M-distill",
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, dict) and "generated_text" in result:
                text = result["generated_text"].strip()
                if text and len(text) > 5:
                    return text[:300]
            elif isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and "generated_text" in result[0]:
                    text = result[0]["generated_text"].strip()
                    if text and len(text) > 5:
                        return text[:300]
    
    except Exception as e:
        print(f"[ERROR] HuggingFace BlenderBot failed: {str(e)}")
    
    return None


def get_alt_inference_api(prompt):
    """Alternative free inference API - DistilGPT2."""
    try:
        payload = {"inputs": prompt}
        headers = {"Content-Type": "application/json"}
        
        response = requests.post(
            "https://api-inference.huggingface.co/models/distilgpt2",
            headers=headers,
            json=payload,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("generated_text", prompt).strip()
                # Remove the input prompt if duplicated
                if text.startswith(prompt):
                    text = text[len(prompt):].strip()
                if text and len(text) > 5:
                    return text[:300]
    
    except Exception as e:
        print(f"[ERROR] DistilGPT2 API failed: {str(e)}")
    
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