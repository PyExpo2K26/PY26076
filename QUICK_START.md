# Get Real AI Responses - Quick Start

## 🚀 3-Minute Setup

### 1️⃣ Get Free Groq API Key
- Visit: **https://console.groq.com/keys**
- Sign up (free, no credit card)
- Click "Create API Key" and copy it

### 2️⃣ Update app.py
Open `app.py` and find line 21:
```python
API_KEY = "gsk_REPLACE_WITH_YOUR_GROQ_API_KEY"
```

Replace with your actual key:
```python
API_KEY = "gsk_your_actual_key_here"
```

### 3️⃣ Restart Flask
The server is already running. Just:
- Go to the terminal where Flask is running
- Press `Ctrl+C` to stop it
- Type: `python app.py`
- It will restart with your new key

### 4️⃣ Test It!
- Go to: http://localhost:5000
- Send a message
- You'll get REAL AI responses! 🎉

---

## ✅ What You'll Get

With Groq API:
- ⚡ Real AI responses to your queries
- 🆓 Completely free (generous free tier)
- ⚙️ No setup beyond the API key
- 🚀 Super fast responses
- 💪 Works great for chat applications

---

## 📋 Supported Models (Groq)

The app is configured to use: `mixtral-8x7b-32768`
(Fast, smart, and great for conversation)

If you want to try other models, change line 23 in `app.py`:
```python
MODEL = "mixtral-8x7b-32768"  # Current
MODEL = "llama2-70b-4096"     # More detailed
MODEL = "gemma-7b-it"          # Lightweight
```

---

## ❓ Need Help?

**Still getting mock responses?**
- Make sure you restarted Flask after updating the key
- Check the terminal for error messages
- Verify your API key is correct (copy-paste carefully)

**"Invalid API key" error?**
- Get a new key from https://console.groq.com/keys
- Make sure there are no extra spaces

**Different API provider?**
See `SETUP_AI_API.md` for OpenAI, OpenRouter options.

---

That's it! You now have a working AI chatbot! 🤖✨
