# 🔥 Infini Think Chat Application

A sarcastic multilingual AI chatbot with Flask backend and vanilla HTML/CSS/JavaScript frontend.

## Quick Start

### 1. Install Dependencies
```bash
pip install flask flask-cors requests edge-tts pydub
```

### 2. Start the Flask Server
```bash
python app.py
```

You should see:
```
[*] Infini Think API Server starting on http://localhost:5000...
```

### 3. Open in Browser
Visit: `http://localhost:5000`

## Troubleshooting

### "Server is not running" or Connection Refused
- Make sure Flask is started with `python app.py`
- Check that port 5000 is available
- On Windows, you may need to allow through firewall

### Chatbot Not Responding
1. **Check API Key**: The OpenRouter API key may be invalid/expired
   - Get a new key from: https://openrouter.ai
   - Update `API_KEY` in `app.py` line 21
   
2. **Test the API**:
   ```bash
   python test_api.py
   ```

3. **Check Flask logs**: Look for error messages in the terminal where Flask is running

### CORS Errors
- This is normal during development - Flask handles CORS
- If you see CORS errors, make sure `flask-cors` is installed
- Check the browser console for detailed error messages

### Port Already in Use
If port 5000 is already in use:
```bash
python app.py --port 5001
```
Then visit `http://localhost:5001`

## File Structure

```
PY26076/
├── app.py                 # Flask backend
├── test_api.py           # API testing script
├── templates/
│   └── index.html        # Chat UI template
├── static/
│   ├── css/
│   │   └── style.css     # Chat styling
│   └── js/
│       └── app.js        # Chat logic
├── venom_chat_log.json   # Chat history (auto-created)
└── venom_backend.py      # Legacy voice backend (optional)
```

## Features

✅ Real-time chat interface  
✅ Chat history persistence  
✅ Responsive mobile design  
✅ Typing indicators  
✅ Clear chat history  
✅ Fallback mock responses (when API unavailable)

## Configuration

Edit `app.py` to customize:

- **`API_KEY`**: OpenRouter API key (line 21)
- **`MODEL`**: AI model (line 22) - default: `anthropic/claude-3-haiku`
- **`VOICE`**: TTS voice (line 23) - default: `en-US-GuyNeural`
- **`MAX_HISTORY`**: Chat history size (line 24) - default: 6 messages
- **Port**: Change `app.run(port=5000)` on last line

## API Endpoints

### POST `/api/chat`
Send a message and get a response
```json
{
  "message": "Your message here"
}
```

Response:
```json
{
  "reply": "Bot's response",
  "success": true
}
```

### GET `/api/history`
Get chat history
```json
{
  "history": [...],
  "success": true
}
```

### POST `/api/clear-history`
Clear all chat history
```json
{
  "success": true
}
```

## Switching API Providers

To use a different AI API, modify `get_infini_think_reply()` in `app.py`:

1. Change the request endpoint
2. Update headers and payload format
3. Parse response correctly
4. Update error handling

Mock responses will activate if the API fails, so you can always test the UI.

## License

Feel free to modify and use as needed.
