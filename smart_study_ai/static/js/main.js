// Smart Study AI - Main JavaScript
let currentDomain = 'general';
let currentLanguage = 'english';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const voiceBtn = document.getElementById('voiceBtn');
const langToggle = document.getElementById('langToggle');
const domainList = document.getElementById('domainList');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadDomains();
    setupEventListeners();
    setupVoiceRecognition();
});

function loadDomains() {
    fetch('/domains')
        .then(response => response.json())
        .then(domains => {
            domainList.innerHTML = '';
            for (const [key, domain] of Object.entries(domains)) {
                const domainItem = document.createElement('div');
                domainItem.className = `domain-item ${key === currentDomain ? 'active' : ''}`;
                domainItem.innerHTML = `
                    <span>${domain.icon}</span>
                    <span>${domain.name}</span>
                `;
                domainItem.onclick = () => switchDomain(key);
                domainList.appendChild(domainItem);
            }
        });
}

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    langToggle.addEventListener('click', toggleLanguage);
}

function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(message, 'user');
    userInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to backend
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            domain: currentDomain,
            language: currentLanguage
        })
    })
    .then(response => response.json())
    .then(data => {
        removeTypingIndicator();
        addMessage(data.response, 'bot');
        
        // Trigger 3D animation
        triggerResponseAnimation();
    })
    .catch(error => {
        removeTypingIndicator();
        console.error('Error:', error);
    });
}

function addMessage(content, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message`;
    messageDiv.innerHTML = formatMessage(content);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatMessage(text) {
    // Convert markdown-like formatting
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/\n/g, '<br>');
    text = text.replace(/```(\w+)\n([\s\S]*?)```/g, '<pre><code class="$1">$2</code></pre>');
    return text;
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = 'Smart AI is thinking... 🤔';
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function switchDomain(domain) {
    currentDomain = domain;
    document.querySelectorAll('.domain-item').forEach(item => {
        item.classList.remove('active');
    });
    event.target.closest('.domain-item').classList.add('active');
}

function toggleLanguage() {
    currentLanguage = currentLanguage === 'english' ? 'hindi' : 'english';
    
    fetch('/toggle_language', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ language: currentLanguage })
    });
    
    // Update UI
    const langSpan = document.querySelector('#langToggle span');
    langSpan.textContent = currentLanguage === 'english' ? 'EN/हिं' : 'हिं/EN';
}

function setupVoiceRecognition() {
    if ('webkitSpeechRecognition' in window) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        
        voiceBtn.addEventListener('click', () => {
            recognition.lang = currentLanguage === 'hindi' ? 'hi-IN' : 'en-US';
            recognition.start();
            voiceBtn.style.background = '#ff4444';
        });
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            voiceBtn.style.background = '';
        };
        
        recognition.onend = () => {
            voiceBtn.style.background = '';
        };
    }
}

function triggerResponseAnimation() {
    // Trigger 3D animation from three-setup.js
    if (typeof animateResponse === 'function') {
        animateResponse();
    }
}