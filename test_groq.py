import requests
import os

API_KEY = "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"   # temporarily paste it here just for testing

url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "model": "llama-3.3-70b-versatile",
    "messages": [
        {"role": "user", "content": "Hello from Python"}
    ]
}

response = requests.post(url, headers=headers, json=payload)

print("Status:", response.status_code)
print("Response:")
print(response.text)

