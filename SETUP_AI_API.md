# 🔥 Get Real AI Responses - Setup Guide

## Option 1: Use Groq API (Recommended - Free & Fast)

### Step 1: Get Your Free API Key
1. Go to: **https://console.groq.com/keys**
2. Sign up (or sign in)
3. Click "Create API Key"
4. Copy the API key

### Step 2: Update Your App
1. Open `app.py` (line 21)
2. Replace `gsk_REPLACE_WITH_YOUR_GROQ_API_KEY` with your actual key
3. Save the file

### Step 3: Restart Flask
- Stop the running Flask server (Ctrl+C)
- Run: `python app.py`

### Step 4: Test
Visit `http://localhost:5000` and send a message. You'll get real AI responses!

---

## Option 2: Use OpenAI API (If you have a paid key)

1. Get API key from: https://platform.openai.com/api-keys
2. Update `app.py`:
   - Line 22: Change `API_PROVIDER = "openrouter"` to `API_PROVIDER = "openai"`
   - Line 21: Paste your OpenAI API key
   - Line 23: Change `MODEL = "mixtral-8x7b-32768"` to `MODEL = "gpt-3.5-turbo"`
3. Restart Flask

---

## Option 3: Use OpenRouter (If you have credits)

1. Get API key from: https://openrouter.ai
2. Add credits to your account
3. Update `app.py`:
   - Line 22: Change `API_PROVIDER = "groq"`
   - Line 21: Paste your OpenRouter API key
   - Line 23: Change back to a model like `"anthropic/claude-3-haiku"`
4. Restart Flask

---

## Groq API Free Tier Details

✅ **Completely Free**
✅ **Fast Responses** (< 1 second)
✅ **No Credit Card Required**
✅ **Rate Limit**: 30 requests/minute (more than enough)
✅ **Available Models**:
  - `mixtral-8x7b-32768` (Recommended - fast & smart)
  - `llama2-70b-4096` (More detailed)
  - `gemma-7b-it` (Lightweight)

---

## Troubleshooting

### "Invalid API Key" Error
- Check you copied the key correctly
- Make sure there are no extra spaces
- Try generating a new key from the console

### Still Getting Mock Responses
- Make sure Flask has restarted
- Check the terminal for error messages
- Verify your API key is set correctly

### No Response at All
- Check your internet connection
- Make sure the API provider is online
- Check Flask terminal for error messages

---

## How to Switch APIs Quickly

The app is set up to support multiple APIs. To switch:

```python
# In app.py, line 22:
API_PROVIDER = "groq"  # Change to: "groq", "openrouter", or "openai"
```

That's it! The app will automatically use the correct API endpoint.
