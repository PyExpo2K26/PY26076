// DOM Elements
const messagesDiv = document.getElementById('messages');
const inputField = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');
const chatForm = document.getElementById('chat-form');

// State
let isLoading = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    inputField.focus();
});

// Load chat history
async function loadHistory() {
    try {
        const response = await fetch('http://localhost:5000/api/history');
        const data = await response.json();
        if (data.success && data.history && data.history.length > 0) {
            // Clear welcome message
            messagesDiv.innerHTML = '';
            // Load history
            data.history.forEach(item => {
                addMessage(item.user, 'user');
                addMessage(item.venom, 'infini');
            });
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
    scrollToBottom();
}

// Send message
async function sendMessage(event) {
    event.preventDefault();
    
    const userMessage = inputField.value.trim();
    if (!userMessage) return;
    
    // Clear welcome if present
    if (messagesDiv.querySelector('.welcome')) {
        messagesDiv.innerHTML = '';
    }
    
    // Add user message
    addMessage(userMessage, 'user');
    inputField.value = '';
    setLoading(true);
    
    // Show typing indicator
    const typingId = showTypingIndicator();
    
    try {
        const response = await fetch('http://localhost:5000/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        if (data.success) {
            addMessage(data.reply, 'infini');
        } else {
            addMessage('Error getting response. Try again.', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator(typingId);
        addMessage('Error getting response. Try again.', 'error');
    } finally {
        setLoading(false);
        inputField.focus();
    }
    
    scrollToBottom();
}

// Add message to chat
function addMessage(text, type = 'user') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Add badge
    const badgeSpan = document.createElement('span');
    badgeSpan.className = 'badge';
    if (type === 'user') {
        badgeSpan.textContent = 'You';
    } else if (type === 'infini') {
        badgeSpan.textContent = '🔥 Infini Think';
    } else if (type === 'error') {
        badgeSpan.textContent = '❌ Error';
    }
    
    // Add message text
    const textPara = document.createElement('p');
    textPara.textContent = text;
    
    contentDiv.appendChild(badgeSpan);
    contentDiv.appendChild(textPara);
    messageDiv.appendChild(contentDiv);
    
    messagesDiv.appendChild(messageDiv);
    scrollToBottom();
}

// Show typing indicator
function showTypingIndicator() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message infini';
    messageDiv.id = 'typing-indicator';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const badgeSpan = document.createElement('span');
    badgeSpan.className = 'badge';
    badgeSpan.textContent = '🔥 Infini Think';
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing';
    for (let i = 0; i < 3; i++) {
        const span = document.createElement('span');
        typingDiv.appendChild(span);
    }
    
    contentDiv.appendChild(badgeSpan);
    contentDiv.appendChild(typingDiv);
    messageDiv.appendChild(contentDiv);
    
    messagesDiv.appendChild(messageDiv);
    scrollToBottom();
    
    return 'typing-indicator';
}

// Remove typing indicator
function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Clear chat
async function clearChat() {
    if (!confirm('Are you sure you want to clear the chat history?')) {
        return;
    }
    
    try {
        const response = await fetch('http://localhost:5000/api/clear-history', {
            method: 'POST'
        });
        
        const data = await response.json();
        if (data.success) {
            messagesDiv.innerHTML = `
                <div class="welcome">
                    <h2>Welcome to Infini Think</h2>
                    <p>Say something to get started!</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Failed to clear history:', error);
        alert('Failed to clear history');
    }
}

// Set loading state
function setLoading(loading) {
    isLoading = loading;
    inputField.disabled = loading;
    sendBtn.disabled = loading;
}

// Scroll to bottom
function scrollToBottom() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Handle Enter key
inputField.addEventListener('keypress', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !isLoading) {
        sendMessage(event);
    }
});
