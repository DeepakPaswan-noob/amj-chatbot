// Student Chatbot JavaScript Functionality
class StudentChatbot {
    constructor() {
    // IDs in `templates/index.html`: user-input, send-btn, chat-body
    this.messageInput = document.getElementById('user-input');
    this.sendButton = document.getElementById('send-btn');
    this.chatMessages = document.getElementById('chat-body');
        
        this.initializeEventListeners();
        this.setWelcomeTime();
    }
    
    initializeEventListeners() {
        // Send button click
        this.sendButton.addEventListener('click', () => this.sendMessage());
        
        // Enter key press
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendMessage();
            }
        });
        
        // Input focus events
        this.messageInput.addEventListener('focus', () => {
            this.messageInput.parentElement.style.borderColor = '#4f46e5';
        });
        
        this.messageInput.addEventListener('blur', () => {
            this.messageInput.parentElement.style.borderColor = '#e2e8f0';
        });
    }
    
    setWelcomeTime() {
        const welcomeTimeElement = document.getElementById('welcomeTime');
        if (welcomeTimeElement) {
            welcomeTimeElement.textContent = this.formatTime(new Date());
        }
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message) {
            this.showError('Please enter a message');
            return;
        }
        
        // Disable input while processing
        this.setInputState(false);
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        
        try {
            // Send message to backend
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // Add bot response immediately; data may include faq_id
            this.addMessage(data.response, 'bot');
            if (data.faq_id) {
                // attach vote handlers (example)
                // (message container is last child)
                const last = this.chatMessages.lastElementChild;
                const voteBtns = last.querySelectorAll('.vote-btn');
                if (voteBtns.length === 2) {
                    voteBtns[0].addEventListener('click', ()=> postVote(data.faq_id, true));
                    voteBtns[1].addEventListener('click', ()=> postVote(data.faq_id, false));
                }
            }
            this.setInputState(true);
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.addMessage(
                'Sorry, I\'m having trouble connecting right now. Please try again in a moment.',
                'bot'
            );
            this.setInputState(true);
        }
    }
    
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        // Create avatar for both user and bot messages. Bot will use the college logo image
        // located at /static/images/AMJ-college-logo-White-150x150.png if available. If the
        // image fails to load, fall back to a neutral SVG avatar.
        // Show avatar for both user and bot messages. Bot will use `chatbot-logo.png`.
        let avatarDiv = document.createElement('div');
        avatarDiv.className = 'message-avatar';
        if (sender === 'bot') {
            const img = document.createElement('img');
            img.src = '/static/images/chatbot-logo.png';
            img.dataset.fallbackTried = 'false';
            img.onerror = function(){
                if (this.dataset.fallbackTried === 'false'){
                    this.dataset.fallbackTried = 'true';
                    this.src = '/chatbot-logo.png';
                    return;
                }
                try { this.remove(); } catch(e){}
                avatarDiv.innerHTML = `\n                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">\n                        <circle cx="12" cy="12" r="10" fill="#60a5fa" />\n                        <text x="12" y="16" text-anchor="middle" font-size="9" font-family="Arial, Helvetica, sans-serif" fill="#fff">AMJ</text>\n                    </svg>`;
            };
            img.alt = 'Chatbot logo';
            img.className = 'message-avatar-img';
            avatarDiv.appendChild(img);
        } else {
            avatarDiv.innerHTML = `\n                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">\n                    <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 20a8 8 0 0 1 16 0" fill="#fff" opacity="0.95"/>\n                </svg>`;
        }

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        if (sender === 'bot') {
            textDiv.innerHTML = this.formatMessage(text); // backend returns safe HTML
        } else {
            textDiv.textContent = text;
        }
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time';
        timeDiv.textContent = this.formatTime(new Date());
        
        contentDiv.appendChild(textDiv);
        contentDiv.appendChild(timeDiv);
        
    // Append avatar if it exists (user messages). Bot messages will not have an avatar element.
    if (avatarDiv) messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(contentDiv);
        
        // Add with animation class and slight delay to allow CSS animation
        messageDiv.style.willChange = 'transform, opacity';
        this.chatMessages.appendChild(messageDiv);
        // Trigger a reflow then let CSS animate
        requestAnimationFrame(() => {
            messageDiv.classList.add('pop');
        });

        // Robust scroll: wait a frame then scroll the newly added message into view.
        // Using scrollIntoView is more reliable across mobile browsers.
        requestAnimationFrame(() => {
            try {
                // smooth scroll into view; fallback to instant after animation
                messageDiv.scrollIntoView({ behavior: 'smooth', block: 'end', inline: 'nearest' });
                setTimeout(() => {
                    // final snap to ensure visible
                    messageDiv.scrollIntoView({ behavior: 'auto', block: 'end', inline: 'nearest' });
                }, 420);
            } catch (e) {
                // fallback to container scroll
                this.scrollToBottom(true);
                setTimeout(() => this.scrollToBottom(false), 350);
            }
        });
    }
    
    formatMessage(text) {
        // Convert line breaks to HTML and allow HTML content
        return text.replace(/\n/g, '<br>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit',
            hour12: true 
        });
    }
    
    setInputState(enabled) {
        this.messageInput.disabled = !enabled;
        this.sendButton.disabled = !enabled;
        
        if (enabled) {
            this.messageInput.focus();
        }
    }
    
    scrollToBottom() {
        // default to instant scroll; pass true for smooth
        const smooth = arguments[0] === true;
        setTimeout(() => {
            if (smooth && 'scrollTo' in this.chatMessages) {
                this.chatMessages.scrollTo({ top: this.chatMessages.scrollHeight, behavior: 'smooth' });
            } else {
                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            }
        }, 80);
    }
    
    showError(message) {
        // Simple error notification
        const errorDiv = document.createElement('div');
        errorDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        errorDiv.textContent = message;
        
        document.body.appendChild(errorDiv);
        
        setTimeout(() => {
            errorDiv.remove();
        }, 3000);
    }
}

async function postVote(faq_id, helpful){
    await fetch('/api/vote', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({faq_id, helpful})});
}

// Export handlers
// CSV export handler removed — feature not required

// Suggestion functions
function sendSuggestion(message) {
    const chatbot = window.chatbotInstance;
    if (chatbot) {
        chatbot.messageInput.value = message;
        chatbot.sendMessage();
    }
}

// Initialize chatbot when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatbotInstance = new StudentChatbot();
    
    // Add some interactive features
    addInteractiveFeatures();
    wireWidgetToggle();
});

function addInteractiveFeatures() {
    // Add hover effects to suggestion chips
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    suggestionChips.forEach(chip => {
        chip.addEventListener('mouseenter', () => {
            chip.style.transform = 'translateY(-2px)';
        });
        
        chip.addEventListener('mouseleave', () => {
            chip.style.transform = 'translateY(0)';
        });
    });
    
    // Add keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Alt + C to focus on input
        if (e.altKey && e.key === 'c') {
            e.preventDefault();
            document.getElementById('user-input').focus();
        }
        
        // Escape to clear input
        if (e.key === 'Escape') {
            document.getElementById('user-input').value = '';
            document.getElementById('user-input').blur();
        }
    });
    
    // Add connection status monitoring
    monitorConnectionStatus();

    // Wire quick-reply buttons present in the UI
    document.querySelectorAll('.quick').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const q = btn.dataset.q || btn.textContent.trim();
            const input = document.getElementById('user-input');
            input.value = q;
            // send via the chatbot instance
            if (window.chatbotInstance) window.chatbotInstance.sendMessage();
        });
    });
}

function monitorConnectionStatus() {
    let isOnline = navigator.onLine;
    
    function updateStatus() {
        const statusElement = document.querySelector('.status');
        if (statusElement) {
            if (navigator.onLine) {
                statusElement.textContent = 'Online • Ready to help';
                statusElement.style.color = '#10b981';
            } else {
                statusElement.textContent = 'Offline • Please check connection';
                statusElement.style.color = '#ef4444';
            }
        }
    }
    
    window.addEventListener('online', updateStatus);
    window.addEventListener('offline', updateStatus);
    
    // Initial status check
    updateStatus();
}

// Widget toggle behavior
function wireWidgetToggle(){
    const toggle = document.getElementById('chat-toggle');
    if (!toggle) return;

    function openWidget(){
        document.body.classList.add('widget-open');
        // focus input
        setTimeout(()=> document.getElementById('user-input')?.focus(), 120);
        toggle.setAttribute('aria-label','Close chat');
    }

    function closeWidget(){
        document.body.classList.remove('widget-open');
        toggle.setAttribute('aria-label','Open chat');
    }

    toggle.addEventListener('click', ()=>{
        if (document.body.classList.contains('widget-open')) closeWidget(); else openWidget();
    });

    // Close on Escape
    document.addEventListener('keydown', (e)=>{
        if (e.key === 'Escape' && document.body.classList.contains('widget-open')){
            closeWidget();
        }
    });

    // Close when clicking outside the chat app (for larger screens)
    document.addEventListener('click', (e)=>{
        if (!document.body.classList.contains('widget-open')) return;
        const app = document.querySelector('.chat-app');
        const isToggle = e.target.closest('#chat-toggle');
        if (!app.contains(e.target) && !isToggle) closeWidget();
    });
}

// Utility functions for enhanced UX
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Copied to clipboard!');
    }).catch(() => {
        console.error('Failed to copy text');
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
        font-family: 'Inter', sans-serif;
        font-size: 14px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    `;
    
    const colors = {
        info: '#3b82f6',
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b'
    };
    
    notification.style.background = colors[type] || colors.info;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS for notifications
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyles);
