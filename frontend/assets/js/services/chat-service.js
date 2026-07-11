/**
 * Chat Service
 * Handles all chatbot API communication
 */

class ChatService {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
        this.chatbotEndpoint = window.config.get('chatbotEndpoint');
    }

    /**
     * Send message to chatbot and get response
     * @param {string} message - User message
     * @param {string} userId - User ID
     * @returns {Promise<Object>} Chatbot response
     */
    async sendMessage(message, userId) {
        const requestUrl = `${this.chatbotEndpoint}/chat`;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': userId
                },
                body: JSON.stringify({
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`Chat API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Chat API response received:', data);
            return data;

        } catch (error) {
            console.error('🔴 Chat API error:', error);
            throw error;
        }
    }

    /**
     * Get streaming chat response (Server-Sent Events)
     * @param {string} message - User message
     * @param {string} userId - User ID
     * @param {Function} onMessage - Callback for each message chunk
     * @param {Function} onComplete - Callback when stream completes
     * @param {Function} onError - Callback for errors
     * @returns {Promise<void>}
     */
    async streamMessage(message, userId, onMessage, onComplete, onError) {
        const requestUrl = `${this.chatbotEndpoint}/chat/stream?message=${encodeURIComponent(message)}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'X-User-ID': userId
                }
            });

            if (!response.ok) {
                throw new Error(`Stream API failed: ${response.status} ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    if (onComplete) onComplete();
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.substring(6));
                            if (onMessage) onMessage(data);
                        } catch (parseError) {
                            console.error('Failed to parse SSE data:', parseError);
                        }
                    }
                }
            }

        } catch (error) {
            console.error('🔴 Stream API error:', error);
            if (onError) onError(error);
        }
    }

    /**
     * Save chat message to database
     * @param {string} userId - User ID
     * @param {string} userMessage - User's message
     * @param {string} botResponse - Bot's response
     * @param {string|null} intent - Detected intent
     * @param {Object|null} entities - Detected entities
     * @returns {Promise<boolean>} Success status
     */
    async saveChatMessage(userId, userMessage, botResponse, intent = null, entities = null) {
        const requestUrl = `${this.apiEndpoint}/api/chat/`;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-User-ID': userId
                },
                body: JSON.stringify({
                    user_id: userId,
                    user_message: userMessage,
                    bot_response: botResponse,
                    intent: intent,
                    entities: entities
                })
            });

            if (response.ok) {
                console.log('✅ Chat saved to database successfully');
                return true;
            } else {
                const errorData = await response.json().catch(() => ({}));
                console.error('Failed to save chat:', response.status, errorData.detail || 'Unknown error');
                return false;
            }

        } catch (error) {
            console.error('🔴 Failed to save chat:', error);
            return false;
        }
    }

    /**
     * Reset conversation history
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} Reset response
     */
    async resetConversation(token) {
        const requestUrl = `${this.chatbotEndpoint}/reset`;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Reset API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Conversation reset successfully');
            return data;

        } catch (error) {
            console.error('🔴 Reset conversation error:', error);
            throw error;
        }
    }
}

// Export singleton instance
window.chatService = new ChatService();