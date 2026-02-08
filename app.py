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
HISTORY_FILE = "infini_think_chat_log.json"
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
    reply = process_query(user_message)
    
    return jsonify({'reply': reply, 'success': True})

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

if __name__ == '__main__':
    # Using debug=True is helpful during development
    app.run(debug=True, port=5000)
