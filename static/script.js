let apiKey = localStorage.getItem('gemini_api_key');

document.addEventListener('DOMContentLoaded', () => {
    if (!apiKey) {
        showConfig();
    } else {
        // Send key to backend to initialize session
        updateBackendConfig(apiKey);
    }
});

function showConfig() {
    document.getElementById('config-modal').classList.remove('hidden');
}

function closeConfig() {
    document.getElementById('config-modal').classList.add('hidden');
}

async function saveConfig() {
    const key = document.getElementById('api-key-input').value.trim();
    if (key) {
        apiKey = key;
        localStorage.setItem('gemini_api_key', key);
        await updateBackendConfig(key);
        closeConfig();
    }
}

async function updateBackendConfig(key) {
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apiKey: key })
        });
    } catch (e) {
        console.error("Error setting config", e);
    }
}

function handleKeyPress(e) {
    if (e.key === 'Enter') sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    // Add User Message
    addMessage('user', text);
    input.value = '';

    // Add Loading Indicator
    const loadingId = addLoading();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        removeMessage(loadingId);

        if (data.error) {
            if (data.error === 'API_KEY_MISSING') {
                addMessage('bot', '⚠️ Necesito tu API Key para funcionar. Por favor configúrala arriba.');
                showConfig();
            } else {
                addMessage('bot', `❌ Error: ${data.message || 'Algo salió mal.'}`);
            }
        } else {
            // Show tool calls if any
            if (data.tool_calls && data.tool_calls.length > 0) {
                const toolsHtml = data.tool_calls.map(tc =>
                    `<div class="tool-call">🛠️ Usando: ${tc.tool}</div>`
                ).join('');
                addMessage('bot', toolsHtml + data.response, true);
            } else {
                addMessage('bot', data.response);
            }
        }

    } catch (error) {
        removeMessage(loadingId);
        addMessage('bot', '❌ Error de conexión con el servidor.');
    }
}

function addMessage(role, text, isHtml = false) {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = `message ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? '👤' : '🤖';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (isHtml) {
        // If it's explicitly HTML (like our tool call logs), use it directly
        bubble.innerHTML = text;
    } else {
        // For model responses, ALWAYS parse Markdown
        // Configure marked to handle line breaks correctly
        marked.setOptions({
            breaks: true,
            gfm: true
        });
        bubble.innerHTML = marked.parse(text);
    }

    div.appendChild(avatar);
    div.appendChild(bubble);
    container.appendChild(div);

    container.scrollTop = container.scrollHeight;
    return div.id = 'msg-' + Date.now();
}

function addLoading() {
    const container = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'message bot';
    div.innerHTML = `
        <div class="avatar">🤖</div>
        <div class="bubble">
            <div class="typing-indicator">
                <div class="dot"></div><div class="dot"></div><div class="dot"></div>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return div.id = 'loading-' + Date.now();
}

function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
