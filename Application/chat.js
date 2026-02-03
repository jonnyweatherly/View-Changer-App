/**
 * View Changer App - Chat Interface
 * 
 * Handles:
 * - Chat message sending and receiving
 * - NDJSON streaming response parsing
 * - Tool result display
 * - Chat history management
 * 
 * Test locally by opening http://localhost:8000 after running:
 *   uvicorn main:app --reload --port 8000
 */

// --- State ---
const chatState = {
    messages: [],
    isProcessing: false
};

// --- DOM Elements ---
const chatElements = {
    messagesContainer: document.getElementById('chatMessages'),
    input: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    statusIndicator: document.getElementById('chatStatus')
};

// --- Chat Functions ---

/**
 * Send a message to the AI chat endpoint
 * @param {string} message - The user's message
 */
async function sendMessage(message) {
    if (!message.trim() || chatState.isProcessing) return;

    // Set processing state
    chatState.isProcessing = true;
    updateStatus('thinking');

    // Add user message to UI
    appendMessage('user', message);

    // Add to history
    chatState.messages.push({
        role: 'user',
        content: message
    });

    // Clear input
    chatElements.input.value = '';

    // Show typing indicator
    const typingId = showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                messages: chatState.messages
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Chat request failed');
        }

        // Remove typing indicator
        removeTypingIndicator(typingId);

        // Parse streaming NDJSON response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let assistantContent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const data = JSON.parse(line);

                    if (data.type === 'tool_result') {
                        // Show tool execution notification
                        showToolResult(data.name, data.result);

                        // Refresh the view after tool execution
                        if (window.APP) {
                            await window.APP.fetchViewColumns();
                        }
                    } else if (data.type === 'reply') {
                        // Show the AI's response
                        assistantContent = data.content;
                        appendMessage('bot', data.content);
                    } else if (data.type === 'error') {
                        throw new Error(data.content);
                    }
                } catch (parseError) {
                    console.error('Error parsing line:', line, parseError);
                }
            }
        }

        // Add assistant response to history
        if (assistantContent) {
            chatState.messages.push({
                role: 'assistant',
                content: assistantContent
            });
        }

    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator(typingId);
        appendMessage('bot', `Sorry, I encountered an error: ${error.message}`);

        if (window.APP) {
            window.APP.showToast(error.message, 'error');
        }
    }

    // Reset processing state
    chatState.isProcessing = false;
    updateStatus('ready');
}

/**
 * Append a message to the chat container
 * @param {string} type - 'user' or 'bot'
 * @param {string} content - The message content
 */
function appendMessage(type, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    const avatarSvg = type === 'bot'
        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';

    messageDiv.innerHTML = `
        <div class="message-avatar">
            ${avatarSvg}
        </div>
        <div class="message-content">
            ${formatMessageContent(content)}
        </div>
    `;

    chatElements.messagesContainer.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Format message content (basic markdown support)
 */
function formatMessageContent(content) {
    if (!content) return '';

    // Escape HTML first
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Convert markdown-like formatting
    formatted = formatted
        // Bold
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        // Code
        .replace(/`(.*?)`/g, '<code>$1</code>')
        // Line breaks
        .replace(/\n/g, '<br>')
        // Lists
        .replace(/^- (.*)$/gm, '<li>$1</li>');

    // Wrap lists
    formatted = formatted.replace(/(<li>.*<\/li>)+/g, '<ul>$&</ul>');

    return formatted;
}

/**
 * Show a tool result notification
 */
function showToolResult(toolName, result) {
    const toolDiv = document.createElement('div');
    toolDiv.className = 'message bot-message';

    const friendlyName = toolName.replace(/_/g, ' ');
    const isSuccess = result.success || (result.data && !result.error);

    toolDiv.innerHTML = `
        <div class="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="tool-badge">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    ${isSuccess
            ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
            : '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'}
                </svg>
                ${friendlyName}
            </div>
            <p style="font-size: 0.875rem; color: var(--text-secondary);">${getToolResultSummary(toolName, result)}</p>
        </div>
    `;

    chatElements.messagesContainer.appendChild(toolDiv);
    scrollToBottom();
}

/**
 * Get a human-readable summary of a tool result
 */
function getToolResultSummary(toolName, result) {
    if (result.error) {
        return result.error;
    }

    const data = result.data;

    switch (toolName) {
        case 'list_available_columns':
            return `Found ${data?.length || 0} available columns`;
        case 'list_view_columns':
            return `View has ${data?.length || 0} columns configured`;
        case 'add_column_to_view':
            return data?.message || 'Column added successfully';
        case 'remove_column_from_view':
            return data?.message || 'Column removed successfully';
        case 'update_column_order':
            return data?.message || 'Column order updated';
        case 'update_column_width':
            return data?.message || 'Column width updated';
        case 'get_column_info':
            return `Found ${data?.length || 0} matching columns`;
        default:
            return 'Action completed';
    }
}

/**
 * Show typing indicator
 */
function showTypingIndicator() {
    const id = 'typing-' + Date.now();
    const typingDiv = document.createElement('div');
    typingDiv.id = id;
    typingDiv.className = 'message bot-message';
    typingDiv.innerHTML = `
        <div class="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                <line x1="9" y1="9" x2="9.01" y2="9"/>
                <line x1="15" y1="9" x2="15.01" y2="9"/>
            </svg>
        </div>
        <div class="message-content">
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;

    chatElements.messagesContainer.appendChild(typingDiv);
    scrollToBottom();
    return id;
}

/**
 * Remove typing indicator
 */
function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

/**
 * Update the status indicator
 */
function updateStatus(status) {
    if (!chatElements.statusIndicator) return;

    if (status === 'thinking') {
        chatElements.statusIndicator.classList.add('thinking');
        chatElements.statusIndicator.innerHTML = `
            <span class="status-dot"></span>
            Thinking...
        `;
    } else {
        chatElements.statusIndicator.classList.remove('thinking');
        chatElements.statusIndicator.innerHTML = `
            <span class="status-dot"></span>
            Ready
        `;
    }
}

/**
 * Scroll chat to bottom
 */
function scrollToBottom() {
    chatElements.messagesContainer.scrollTop = chatElements.messagesContainer.scrollHeight;
}

// --- Event Listeners ---

chatElements.sendBtn?.addEventListener('click', () => {
    sendMessage(chatElements.input.value);
});

chatElements.input?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage(chatElements.input.value);
    }
});

// Disable send button while processing
const originalSendBtnHTML = chatElements.sendBtn?.innerHTML;
function updateSendButton() {
    if (!chatElements.sendBtn) return;

    if (chatState.isProcessing) {
        chatElements.sendBtn.disabled = true;
        chatElements.sendBtn.innerHTML = `
            <div class="loading-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
    } else {
        chatElements.sendBtn.disabled = false;
        chatElements.sendBtn.innerHTML = originalSendBtnHTML;
    }
}

// Watch for processing state changes
setInterval(updateSendButton, 100);

// --- Initialize ---
console.log('Chat module loaded');
