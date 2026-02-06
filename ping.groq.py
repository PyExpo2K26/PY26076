import requests

API_KEY = ""

r = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": "Reply with the word OK only"}
        ],
        "max_tokens": 10
    },
    timeout=30
)

print("STATUS:", r.status_code)
print("TEXT:", r.text)