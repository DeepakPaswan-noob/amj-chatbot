const chatbotBtn = document.getElementById('chatbot-btn');
const chatbox = document.getElementById('chatbox');
const chatboxBody = document.getElementById('chatbox-body');
const chatboxInput = document.getElementById('chatbox-input');
const chatboxSend = document.getElementById('chatbox-send');

chatbotBtn.onclick = () => {
    chatbox.style.display = chatbox.style.display === 'flex' ? 'none' : 'flex';
    if (chatbox.style.display === 'flex') {
        chatboxInput.focus();
    }
};

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${sender}`;
    // render HTML answers from backend and add vote buttons
    const span = document.createElement('span');
    if (sender === 'bot') {
        // text may be object {html, faq_id} or string
        let faq_id = null;
        if (typeof text === 'object'){
            faq_id = text.faq_id;
            span.innerHTML = text.html || '';
        } else {
            span.innerHTML = text;
        }
        const voteBar = document.createElement('div');
        voteBar.className = 'vote-bar';
        const up = document.createElement('button'); up.className='vote-btn'; up.textContent='Helpful 👍';
        const down = document.createElement('button'); down.className='vote-btn'; down.textContent='Not helpful 👎';
        if (faq_id) {
            up.addEventListener('click', ()=> postVote(faq_id, true));
            down.addEventListener('click', ()=> postVote(faq_id, false));
        }
        voteBar.appendChild(up); voteBar.appendChild(down);
        msgDiv.appendChild(span);
        msgDiv.appendChild(voteBar);
    } else {
        span.textContent = text;
        msgDiv.appendChild(span);
    }
    chatboxBody.appendChild(msgDiv);
    chatboxBody.scrollTop = chatboxBody.scrollHeight;
}

function sendMessage() {
    const text = chatboxInput.value.trim();
    if (!text) return;
    addMessage(text, 'user');
    chatboxInput.value = '';
    fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
    })
    .then(res => res.json())
    .then(data => {
        addMessage(data.response, 'bot');
    });
}

chatboxSend.onclick = sendMessage;
chatboxInput.onkeydown = function(e) {
    if (e.key === 'Enter') sendMessage();
};

// Initial greeting
addMessage('Hi! Ask me about admissions, fees, courses, or contact.', 'bot');

function postVote(faq_id, helpful){
    fetch('/api/vote', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({faq_id, helpful})});
}

// export handlers removed
