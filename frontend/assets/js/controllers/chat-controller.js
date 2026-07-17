/**
 * Chat Controller
 * Handles chat functionality for the dashboard
 * Manages message sending, receiving, and display
 */
class ChatController {
    constructor(userId, chatbotEndpoint) {
        this.userId = userId;
        this.chatbotEndpoint = chatbotEndpoint;

        // Message queue to prevent race conditions
        this.pendingMessages = new Map(); // messageId -> { message, timestamp }

        // UI elements
        this.ui = {
            input: document.getElementById('chatInput'),
            button: document.getElementById('sendChatButton'),
            messages: document.getElementById('chatMessages')
        };

        // Initialize
        this.init();
    }

    /**
     * Initialize chat controller
     */
    async init() {
        console.log('💬 Initializing Chat Controller...');

        // Setup event listeners
        this.setupEventListeners();

        console.log('✅ Chat controller initialized');
    }

    /**
     * Setup event listeners for chat
     */
    setupEventListeners() {
        if (this.ui.button && this.ui.input) {
            // Send button click
            this.ui.button.addEventListener('click', () => {
                this.handleSend();
            });

            // Enter key to send (Shift+Enter for new line)
            this.ui.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSend();
                }
            });
        }
    }

    /**
     * Handle send message action
     */
    async handleSend() {
        const message = this.ui.input.value.trim();
        if (!message) {
            console.warn('⚠️ Empty message, skipping send');
            return;
        }

        // Disable input to prevent double submit
        this.setLoadingState(true);

        try {
            this.ui.input.value = '';
            await this.sendMessage(message);
        } finally {
            this.setLoadingState(false);
            this.ui.input.focus();
        }
    }

    /**
     * Manage input UI loading state
     */
    setLoadingState(isLoading) {
        if (this.ui.input) this.ui.input.disabled = isLoading;
        if (this.ui.button) {
            this.ui.button.disabled = isLoading;
            this.ui.button.style.opacity = isLoading ? '0.5' : '1';
        }
    }

    /**
     * Send message via REST API
     */
    async sendMessage(message) {
        console.log('💬 ChatController sendMessage called:', { message, endpoint: this.chatbotEndpoint });

        if (!message.trim()) {
            console.warn('⚠️ Empty message, skipping send');
            return;
        }

        // Generate unique message ID for this request
        const messageId = window.generateUUID();

        // Store message data in queue with timestamp
        this.pendingMessages.set(messageId, {
            message: message,
            timestamp: Date.now()
        });

        // Display user message
        this.displayUserMessage(message);

        // Display typing indicator
        const indicatorId = `typing-${messageId}`;
        this.displayTypingIndicator(indicatorId);

        // Send to chatbot via REST API
        console.log('🔵 Sending chat API request:', {
            endpoint: `${this.chatbotEndpoint}/chat`,
            method: 'POST',
            userId: this.userId,
            messageId: messageId
        });

        try {
            const response = await fetch(`${this.chatbotEndpoint}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': this.userId
                },
                body: JSON.stringify({
                    message: message,
                    context: { user_id: this.userId }
                })
            });

            console.log('🟢 Chat API Response:', {
                status: response.status,
                ok: response.ok,
                statusText: response.statusText
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const responseData = await response.json();
            console.log('🟢 Chat Response Data:', responseData);
            this.removeTypingIndicator(indicatorId);
            this.handleChatbotResponse(responseData, messageId);

        } catch (error) {
            console.error('🔴 Chat API error:', {
                message: error.message,
                stack: error.stack,
                endpoint: this.chatbotEndpoint
            });

            this.removeTypingIndicator(indicatorId);
            // Remove from queue on error
            this.pendingMessages.delete(messageId);

            this.displayBotMessage('Sorry, I encountered an error processing your message. Please try again.');
        }
    }

    /**
     * Handle chatbot response
     */
    handleChatbotResponse(response, messageId) {
        const botMessage = response.response || 'No response received';
        const intent = response.intent || null;
        const confidence = response.confidence || 0;

        this.displayBotMessage(botMessage);

        // Get the original user message from queue using messageId
        const messageData = this.pendingMessages.get(messageId);

        if (messageData) {
            // Save chat to database with the correct user message
            this.saveChatToDatabase(messageData.message, botMessage, intent, messageData.entities || null);

            // Remove from queue after successful processing
            this.pendingMessages.delete(messageId);

            console.log(`✅ Processed message ${messageId} and saved to database`);
        } else {
            console.warn(`No message data found for messageId ${messageId}, skipping database save`);
        }
    }

    /**
     * Display bot message in chat
     */
    displayBotMessage(message) {
        if (!this.ui.messages) return;

        const now = new Date();
        const timeStr = now.toISOString().split('T')[1].split('.')[0] + ' UTC';

        const messageHTML = `
            <div class="flex gap-6">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20">
                    <span class="material-symbols-outlined text-primary" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-4">
                    <div class="flex items-baseline gap-3">
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-primary">Sentinel_AI</span>
                        <span class="text-[10px] text-outline">${timeStr}</span>
                    </div>
                    <div class="bg-surface-container p-4 rounded-2xl border-l-2 border-primary">
                        <p class="text-sm leading-relaxed text-on-surface">${this.escapeHtml(message)}</p>
                    </div>
                </div>
            </div>
        `;

        this.ui.messages.insertAdjacentHTML('beforeend', messageHTML);
        this.ui.messages.scrollTop = this.ui.messages.scrollHeight;
    }

    /**
     * Display typing indicator
     */
    displayTypingIndicator(id) {
        if (!this.ui.messages) return;
        const typingHTML = `
            <div id="${id}" class="flex gap-6">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20">
                    <span class="material-symbols-outlined text-primary" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-4">
                    <div class="bg-surface-container p-4 rounded-2xl border-l-2 border-primary inline-block">
                        <div class="flex space-x-1 items-center h-4">
                            <div class="w-2 h-2 bg-primary/50 rounded-full animate-bounce"></div>
                            <div class="w-2 h-2 bg-primary/50 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                            <div class="w-2 h-2 bg-primary/50 rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        this.ui.messages.insertAdjacentHTML('beforeend', typingHTML);
        this.ui.messages.scrollTop = this.ui.messages.scrollHeight;
    }

    /**
     * Remove typing indicator
     */
    removeTypingIndicator(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    /**
     * Display user message in chat
     */
    displayUserMessage(message) {
        if (!this.ui.messages) return;

        const now = new Date();
        const timeStr = now.toISOString().split('T')[1].split('.')[0] + ' UTC';

        const messageHTML = `
            <div class="flex gap-6 flex-row-reverse">
                <div class="w-10 h-10 rounded-lg bg-surface-container-highest flex items-center justify-center shrink-0">
                    <span class="material-symbols-outlined text-on-surface-variant" aria-hidden="true">person</span>
                </div>
                <div class="flex-1 space-y-4 text-right">
                    <div class="flex items-baseline gap-3 justify-end">
                        <span class="text-[10px] text-outline">${timeStr}</span>
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-on-surface">You</span>
                    </div>
                    <div class="bg-secondary-container p-4 rounded-2xl inline-block text-left max-w-lg">
                        <p class="text-sm leading-relaxed text-on-surface">${this.escapeHtml(message)}</p>
                    </div>
                </div>
            </div>
        `;

        this.ui.messages.insertAdjacentHTML('beforeend', messageHTML);
        this.ui.messages.scrollTop = this.ui.messages.scrollHeight;
    }

    /**
     * Save chat message to database
     */
    async saveChatToDatabase(userMessage, botResponse, intent, entities) {
        const apiEndpoint = window.config.get('apiEndpoint');
        const requestUrl = `${apiEndpoint}/api/chat/`;

        console.log('💾 Saving chat to database:', {
            endpoint: requestUrl,
            userId: this.userId,
            messageLength: userMessage?.length
        });

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': this.userId
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    user_message: userMessage,
                    bot_response: botResponse,
                    intent: intent,
                    entities: entities
                })
            });

            console.log('🟢 Save Chat API Response:', {
                status: response.status,
                ok: response.ok
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Failed to save chat:', response.status, errorData.detail || 'Unknown error');
            } else {
                console.log('✅ Chat saved to database successfully');
            }
        } catch (error) {
            console.error('🔴 Failed to save chat:', {
                message: error.message,
                stack: error.stack,
                endpoint: requestUrl
            });
        }
    }

    /**
     * Escape HTML to prevent XSS (using global utility)
     */
    escapeHtml(text) {
        return window.escapeHtml(text);
    }

    /**
     * Cleanup resources when controller is destroyed
     */
    cleanup() {
        // Clear pending messages
        this.pendingMessages.clear();

        console.log('✅ Chat controller cleaned up');
    }
}