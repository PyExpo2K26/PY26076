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
MODEL = "meta-llama/Llama-3.1-8B-Instruct"
HISTORY_FILE = "infini_think_chat_log.json"
MAX_HISTORY = 6
HF_TOKEN = "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"

MOCK_RESPONSES = [
    "My brain is not braining right now.",
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
                    messages.append({"role": "user", "content": item['user']})
                    messages.append({"role": "assistant", "content": item['infini_think']})
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
    data.append({"timestamp": str(datetime.now()), "user": user_text, "infini_think": reply_text})
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

# --- Primary API Call ---
def get_free_inference_api(prompt, context_messages):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
        "X-Wait-For-Model": "true"
    }
    
    messages = [{"role": "system", "content": "You are Infini Think, a witty AI assistant."}]
    if context_messages:
        messages.extend(context_messages)
    messages.append({"role": "user", "content": prompt})
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300,
        "options": {"wait_for_model": True}
    }
    
    try:
        response = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions",
            headers=headers, json=payload, timeout=60 
        )
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            print(f"[ERROR] API {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[ERROR] Primary Request failed: {e}")
    return None

# --- Fallback API Call ---
def get_alt_inference_api(prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "model": "HuggingFaceH4/zephyr-7b-beta",
        "messages": [{"role": "user", "content": prompt}],
        "options": {"wait_for_model": True}
    }
    try:
        response = requests.post(
            "https://router.huggingface.co/hf-inference/v1/chat/completions",
            headers=headers, json=payload, timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
    except: pass
    return None

# --- Main Logic Router ---
def get_infini_think_reply(prompt, context_messages):
    # Try primary
    reply = get_free_inference_api(prompt, context_messages)
    if reply: return reply
    
    # Try fallback
    print("[INFO] Trying fallback...")
    reply = get_alt_inference_api(prompt)
    if reply: return reply
    
    return None

def process_query(text):
    try:
        context = load_context()
        reply = get_infini_think_reply(text, context)
        
        if not reply:
            reply = random.choice(MOCK_RESPONSES)
        
        cleaned_reply = re.sub(r"\*.*?\*", "", reply).strip()
        save_to_json(text, cleaned_reply)
        return cleaned_reply
    except Exception as e:
        print(f"[ERROR] Process failed: {e}")
        return random.choice(MOCK_RESPONSES)

# --- Routes ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Empty message', 'success': False}), 400
    
    reply = process_query(user_message)
    return jsonify({'reply': reply, 'success': True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
