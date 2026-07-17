/**
 * CyberSec Chat Controller
 * Manages real-time AI chat functionality for the dedicated chat page
 */
class ChatController {
    constructor() {
        this.userId = this.getOrCreateUserId();
        this.chatbotEndpoint = this.normalizeChatbotEndpoint(
            window.config.get('chatbotEndpoint')
        );
        this.apiEndpoint = window.config.get('apiEndpoint');

        // Streaming cancellation support
        this.currentEventSource = null;
        this.currentAbortController = null;

        this.init();
    }

    normalizeChatbotEndpoint(endpoint) {
        if (!endpoint || typeof endpoint !== 'string') {
            return endpoint;
        }

        return endpoint.replace(/\/+$/, '').replace(/\/chat$/, '');
    }

    init() {
        this.setupEventListeners();
        this.addWelcomeMessage();
        console.log('Chat controller initialized');
        this.checkQueryParameters();
        this.setupCleanupOnUnload();
    }

    setupCleanupOnUnload() {
        // Cancel ongoing streams when user navigates away
        window.addEventListener('beforeunload', () => {
            this.cancelCurrentStream();
        });

        // Also cancel on page hide (mobile navigation)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.cancelCurrentStream();
            }
        });
    }

    cancelCurrentStream() {
        // Cancel the current streaming request if active
        if (this.currentEventSource) {
            console.log('🛑 Cancelling current stream');
            try {
                this.currentEventSource.close();
            } catch (error) {
                console.warn('Error closing event source:', error);
            }
            this.currentEventSource = null;
        }

        if (this.currentAbortController) {
            try {
                this.currentAbortController.abort();
            } catch (error) {
                console.warn('Error aborting controller:', error);
            }
            this.currentAbortController = null;
        }
    }

    checkQueryParameters() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const messageParam = urlParams.get('message');

            if (messageParam) {
                console.log('📬 Initial message found in query parameters:', messageParam);

                // VALIDATE AND SANITIZE: Check for malicious patterns and validate length
                const sanitized = this.sanitizeMessageParameter(messageParam);

                if (sanitized && sanitized.length > 0 && sanitized.length <= 5000) {
                    // Additional security check for malicious patterns
                    if (!this.containsMaliciousPatterns(sanitized)) {
                        const textarea = document.getElementById('chatInput');
                        if (textarea) {
                            textarea.value = sanitized;
                            // Dispatch input event to resize textarea
                            textarea.dispatchEvent(new Event('input'));
                            setTimeout(() => {
                                this.sendMessage();
                                this.cleanUrlParameters(); // Clean URL after processing
                            }, 300);
                        }
                    } else {
                        console.warn('⚠️ Malicious patterns detected in message parameter, ignoring');
                        this.cleanUrlParameters();
                    }
                } else {
                    console.warn('⚠️ Invalid message parameter length, ignoring');
                    this.cleanUrlParameters();
                }
            }
        } catch (error) {
            console.error('❌ Error processing URL parameters:', error);
            this.cleanUrlParameters();
        }
    }

    /**
     * Sanitize message parameter from URL to prevent XSS attacks
     * @param {string} message - Raw message parameter
     * @returns {string} Sanitized message
     */
    sanitizeMessageParameter(message) {
        if (!message || typeof message !== 'string') return '';

        let sanitized = message.trim();

        // Remove potentially dangerous content
        sanitized = sanitized.replace(/<script[^>]*>.*?<\/script>/gi, '');
        sanitized = sanitized.replace(/on\w+\s*=/gi, ''); // Remove event handlers like onclick=
        sanitized = sanitized.replace(/javascript:/gi, ''); // Remove javascript: protocol

        // Decode HTML entities then re-escape to prevent double encoding
        const textarea = document.createElement('textarea');
        textarea.innerHTML = sanitized;
        sanitized = textarea.value;

        // Final escape using existing escapeHtml method
        return this.escapeHtml(sanitized);
    }

    /**
     * Check if message contains malicious patterns
     * @param {string} message - Message to check
     * @returns {boolean} True if malicious patterns found
     */
    containsMaliciousPatterns(message) {
        if (!message || typeof message !== 'string') return false;

        const maliciousPatterns = [
            /<script[^>]*>/i,
            /javascript:/i,
            /onerror\s*=/i,
            /onload\s*=/i,
            /<iframe/i,
            /<object/i,
            /<embed/i,
            /<svg/i,
            /data:text\//i
        ];

        return maliciousPatterns.some(pattern => pattern.test(message));
    }

    /**
     * Clean URL parameters by removing query string
     */
    cleanUrlParameters() {
        try {
            const cleanUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
            window.history.replaceState({ path: cleanUrl }, '', cleanUrl);
            console.log('✅ URL parameters cleaned');
        } catch (error) {
            console.error('❌ Error cleaning URL parameters:', error);
        }
    }

    getOrCreateUserId() {
        return window.getOrCreateUserId();
    }

    generateUUID() {
        return window.generateUUID();
    }

    setupEventListeners() {
        const sendButton = document.getElementById('sendButton');
        const textarea = document.getElementById('chatInput');
        const newInvestigationBtn = document.getElementById('newInvestigationBtn');

        if (sendButton && textarea) {
            sendButton.addEventListener('click', () => this.sendMessage());
            textarea.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });

            // Auto-resize textarea as user types
            textarea.addEventListener('input', () => {
                textarea.style.height = 'auto';
                textarea.style.height = Math.min(textarea.scrollHeight, 128) + 'px';
            });
        }

        if (newInvestigationBtn) {
            newInvestigationBtn.addEventListener('click', () => this.startNewInvestigation());
        }

        // Setup suggestion chips click event
        const chips = document.querySelectorAll('.suggestion-chip');
        chips.forEach(chip => {
            chip.addEventListener('click', () => {
                const text = chip.innerText;
                const textarea = document.getElementById('chatInput');
                if (textarea) {
                    textarea.value = text;
                    // Auto-resize textarea
                    textarea.dispatchEvent(new Event('input'));
                    this.sendMessage();
                }
            });
        });
    }

    startNewInvestigation() {
        console.log('🔄 Starting new investigation, clearing chat history');

        // Cancel any ongoing streams
        this.cancelCurrentStream();

        const chatContainer = document.getElementById('chatMessages');
        if (chatContainer) {
            // SECURE: Use safe content clearing instead of innerHTML = ''
            if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeClearContent) {
                CyberSecSanitizer.safeClearContent(chatContainer);
            } else {
                chatContainer.innerHTML = ''; // Fallback if sanitizer not loaded
            }
            this.addWelcomeMessage();
            this.scrollToBottom();
        }
    }

    addWelcomeMessage() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const welcomeHTML = `
            <div class="flex gap-6 group animate-fade-in">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20 shadow-[0_4px_12px_rgba(132,253,173,0.05)]">
                    <span class="material-symbols-outlined text-primary" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-2">
                    <div class="flex items-baseline gap-3">
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-primary">Sentinel_AI</span>
                        <span class="text-[10px] text-outline">${new Date().toLocaleTimeString('en-US', {hour12: false})} UTC</span>
                    </div>
                    <div class="bg-surface-container/60 backdrop-blur-md p-6 rounded-2xl border-l-2 border-primary space-y-4 shadow-[0_4px_15px_rgba(0,0,0,0.15)] border border-white/[0.02]">
                        <p class="text-sm leading-relaxed text-on-surface font-semibold">Xin chào! Tôi là trợ lý an ninh mạng CyberSec. Tôi có thể giúp bạn với:</p>
                        <ul class="text-sm leading-relaxed text-on-surface space-y-2 pl-4 list-disc">
                            <li>Kiểm tra URL phishing (sử dụng VirusTotal API)</li>
                            <li>Đánh giá độ mạnh mật khẩu (có kiểm tra password bị lộ)</li>
                            <li>Tra cứu thông tin CVE (sử dụng NIST NVD API)</li>
                            <li>Cung cấp mẹo bảo mật & Phân tích mối đe dọa</li>
                        </ul>
                        <p class="text-sm leading-relaxed text-on-surface">Bạn cần giúp gì hôm nay?</p>
                        <div class="bg-surface-container-low/40 p-3 rounded-lg border border-outline-variant/20">
                            <p class="text-xs text-on-surface-variant flex items-center gap-2">
                                <span class="material-symbols-outlined text-xs text-primary">info</span>
                                <span>Tất cả tính năng đều sử dụng API miễn phí. Dữ liệu được cache để tối ưu hiệu suất.</span>
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', welcomeHTML);
    }

    async sendMessage() {
        const textarea = document.getElementById('chatInput');
        const message = textarea?.value.trim();

        console.log('💬 sendMessage called:', { message, hasTextarea: !!textarea });

        if (!message) {
            console.warn('⚠️ Empty message, skipping send');
            return;
        }

        // Prevent double send
        this.setLoadingState(true);

        try {
            // Cancel any previous stream before starting new one
            this.cancelCurrentStream();

            // Clear textarea and reset height
            if (textarea) {
                textarea.value = '';
                textarea.style.height = 'auto';
            }

            // Add user message
            this.addUserMessage(message);

            // Check if streaming is enabled (default: true for better UX)
            const useStreaming = true;

            if (useStreaming) {
                await this.sendMessageStreaming(message);
            } else {
                await this.sendMessageRegular(message);
            }
        } finally {
            this.setLoadingState(false);
            if (textarea) textarea.focus();
        }
    }

    setLoadingState(isLoading) {
        const textarea = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendButton');
        if (textarea) {
            textarea.disabled = isLoading;
            textarea.style.opacity = isLoading ? '0.6' : '1';
        }
        if (sendButton) {
            sendButton.disabled = isLoading;
            sendButton.style.opacity = isLoading ? '0.5' : '1';
        }
    }

    async sendMessageRegular(message) {
        // Send message using regular POST request (non-streaming)
        // Show typing indicator
        this.showTypingIndicator();

        console.log('🔵 Sending chat API request (regular):', {
            endpoint: `${this.chatbotEndpoint}/chat`,
            method: 'POST',
            body: {
                message: message,
                context: { user_id: this.userId }
            }
        });

        try {
            const response = await fetch(`${this.chatbotEndpoint}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // Note: Authorization and X-User-ID headers are auto-injected by auth.js fetch interceptor
                },
                body: JSON.stringify({
                    message: message,
                    context: { user_id: this.userId }
                })
            });

            // Hide typing indicator before rendering answer
            this.hideTypingIndicator();

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
            this.addBotMessage(responseData.response);

        } catch (error) {
            console.error('🔴 Chat API Error:', {
                message: error.message,
                stack: error.stack,
                endpoint: this.chatbotEndpoint,
                userId: this.userId
            });
            this.hideTypingIndicator();
            this.addBotMessage('Xin lỗi, tôi gặp lỗi khi xử lý tin nhắn của bạn. Vui lòng kiểm tra lại kết nối đến máy chủ hoặc thử lại sau.');
        }
    }

    async sendMessageStreaming(message, retryCount = 0) {
        const MAX_RETRIES = 3;
        // Send message using SSE streaming for real-time token display
        console.log('🔵 Sending chat API request (streaming):', {
            message: message,
            userId: this.userId,
            retryCount: retryCount
        });

        // Cancel any previous stream before starting new one
        if (retryCount === 0) {
            this.cancelCurrentStream();
        }

        // Create bot message container with empty content initially if first try
        const botMessageId = 'bot-message-' + Date.now();
        if (retryCount === 0) {
            this.addStreamingBotMessage(botMessageId);
        }

        try {
            // Create abort controller for this request
            this.currentAbortController = new AbortController();

            // Build streaming URL. Authenticated users receive a short-lived
            // stream ticket so the JWT is not exposed in browser/proxy URLs.
            let streamTicket = null;
            const token = window.authService && window.authService.getToken
                ? await window.authService.getToken()
                : null;
            if (token) {
                const ticketResponse = await fetch(`${this.chatbotEndpoint}/chat/stream-ticket`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    signal: this.currentAbortController.signal
                });
                if (!ticketResponse.ok) {
                    throw new Error(`Stream ticket request failed: ${ticketResponse.status}`);
                }
                const ticketData = await ticketResponse.json();
                streamTicket = ticketData.stream_ticket;
            }

            const sessionId = this.userId;
            let streamUrl = `${this.chatbotEndpoint}/chat/stream?message=${encodeURIComponent(message)}`;
            if (streamTicket) {
                streamUrl += `&stream_ticket=${encodeURIComponent(streamTicket)}`;
            }
            if (sessionId) {
                streamUrl += `&session_id=${encodeURIComponent(sessionId)}`;
            }

            // Create EventSource for SSE
            const eventSource = new EventSource(streamUrl);

            // Store reference for cancellation
            this.currentEventSource = eventSource;

            let fullResponse = '';
            let streamCompleted = false;

            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('📨 Streaming chunk received:', data);

                    if (data.type === 'metadata') {
                        // Metadata received (intent, confidence, etc.)
                        console.log('📊 Response metadata:', data);
                    } else if (data.type === 'chunk') {
                        // Text chunk received
                        fullResponse += data.content;
                        this.updateStreamingMessage(botMessageId, fullResponse);
                    } else if (data.type === 'complete') {
                        // Streaming complete
                        console.log('✅ Streaming complete:', data.full_response);
                        streamCompleted = true;
                        eventSource.close();
                        this.currentEventSource = null;
                        this.currentAbortController = null;
                        this.finalizeStreamingMessage(botMessageId);
                    } else if (data.type === 'error') {
                        // Error occurred
                        console.error('❌ Streaming error:', data.message || data.error);
                        streamCompleted = true;
                        eventSource.close();
                        this.currentEventSource = null;
                        this.currentAbortController = null;
                        this.updateStreamingMessage(
                            botMessageId,
                            data.message || data.error || '❌ Xin lỗi, đã xảy ra lỗi khi xử lý tin nhắn.'
                        );
                    }
                } catch (parseError) {
                    console.error('Error parsing SSE data:', parseError, event.data);
                }
            };

            eventSource.onerror = (error) => {
                console.error('🔴 SSE connection error:', error);
                eventSource.close();
                this.currentEventSource = null;
                this.currentAbortController = null;

                if (!streamCompleted && !fullResponse) {
                    if (retryCount < MAX_RETRIES) {
                        console.warn(`⚠️ SSE connection lost. Retrying... (${retryCount + 1}/${MAX_RETRIES})`);
                        this.updateStreamingMessage(botMessageId, `🔄 Đang thử kết nối lại... (${retryCount + 1}/${MAX_RETRIES})`);
                        setTimeout(() => {
                            this.sendMessageStreaming(message, retryCount + 1);
                        }, 2000);
                    } else {
                        streamCompleted = true;
                        this.hideTypingIndicator();
                        this.updateStreamingMessage(
                            botMessageId,
                            '❌ Xin lỗi, kết nối streaming liên tục thất bại. Vui lòng thử lại sau.'
                        );
                        this.finalizeStreamingMessage(botMessageId);
                    }
                } else if (!streamCompleted && fullResponse) {
                    // Stream was partially received then disconnected. Finalize what we have.
                    streamCompleted = true;
                    this.finalizeStreamingMessage(botMessageId);
                    const chatContainer = document.getElementById('chatMessages');
                    if (chatContainer) {
                        chatContainer.insertAdjacentHTML('beforeend', '<div class="text-xs text-orange-500 text-center my-2">⚠️ Kết nối bị gián đoạn, nội dung có thể không đầy đủ.</div>');
                    }
                }
            };

        } catch (error) {
            console.error('🔴 Streaming setup error:', error);
            this.hideTypingIndicator();
            this.addBotMessage('Xin lỗi, tôi gặp lỗi khi xử lý tin nhắn của bạn. Vui lòng thử lại.');
            this.currentEventSource = null;
            this.currentAbortController = null;
        }
    }

    addUserMessage(message) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const messageHTML = `
            <div class="flex gap-6 group flex-row-reverse animate-fade-in">
                <div class="w-10 h-10 rounded-lg bg-surface-container-highest flex items-center justify-center shrink-0 shadow-[0_4px_12px_rgba(0,0,0,0.2)]">
                    <span class="material-symbols-outlined text-on-surface-variant" aria-hidden="true">person</span>
                </div>
                <div class="flex-1 space-y-2 text-right">
                    <div class="flex items-baseline gap-3 justify-end">
                        <span class="text-[10px] text-outline">${new Date().toLocaleTimeString('en-US', {hour12: false})} UTC</span>
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-on-surface">Bạn</span>
                    </div>
                    <div class="bg-secondary-container/60 backdrop-blur-md p-4 rounded-2xl inline-block text-left max-w-lg shadow-[0_4px_15px_rgba(0,0,0,0.15)] border border-white/[0.04]">
                        <p class="text-sm leading-relaxed text-on-surface">${this.escapeHtml(message)}</p>
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }

    showTypingIndicator() {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        // Prevent duplicates
        this.hideTypingIndicator();

        const indicatorHTML = `
            <div id="typingIndicator" class="flex gap-6 group animate-fade-in">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20 shadow-[0_4px_12px_rgba(132,253,173,0.05)]">
                    <span class="material-symbols-outlined text-primary animate-pulse" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-2">
                    <div class="flex items-baseline gap-3">
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-primary">Sentinel_AI</span>
                        <span class="text-[10px] text-outline">${new Date().toLocaleTimeString('en-US', {hour12: false})} UTC</span>
                    </div>
                    <div class="bg-surface-container/60 backdrop-blur-md p-4 rounded-2xl border-l-2 border-primary inline-block">
                        <div class="flex items-center gap-1.5 px-1 py-1">
                            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-typing-dot" style="animation-delay: 0ms"></span>
                            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-typing-dot" style="animation-delay: 200ms"></span>
                            <span class="w-1.5 h-1.5 rounded-full bg-primary animate-typing-dot" style="animation-delay: 400ms"></span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', indicatorHTML);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.remove();
        }
    }

    addBotMessage(message) {
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const messageHTML = `
            <div class="flex gap-6 group animate-fade-in">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20 shadow-[0_4px_12px_rgba(132,253,173,0.05)]">
                    <span class="material-symbols-outlined text-primary" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-2">
                    <div class="flex items-baseline gap-3">
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-primary">Sentinel_AI</span>
                        <span class="text-[10px] text-outline">${new Date().toLocaleTimeString('en-US', {hour12: false})} UTC</span>
                    </div>
                    <div class="bg-surface-container/60 backdrop-blur-md p-5 rounded-2xl border-l-2 border-primary shadow-[0_4px_15px_rgba(0,0,0,0.15)] border border-white/[0.02]">
                        ${this.renderMarkdown(message)}
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }

    addStreamingBotMessage(messageId) {
        // Add empty bot message container for streaming updates
        const chatContainer = document.getElementById('chatMessages');
        if (!chatContainer) return;

        const messageHTML = `
            <div id="${messageId}" class="flex gap-6 group animate-fade-in">
                <div class="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center shrink-0 border border-primary/20 shadow-[0_4px_12px_rgba(132,253,173,0.05)]">
                    <span class="material-symbols-outlined text-primary streaming-icon animate-pulse" aria-hidden="true">smart_toy</span>
                </div>
                <div class="flex-1 space-y-2">
                    <div class="flex items-baseline gap-3">
                        <span class="font-headline font-bold text-xs uppercase tracking-widest text-primary">Sentinel_AI</span>
                        <span class="text-[10px] text-outline">${new Date().toLocaleTimeString('en-US', {hour12: false})} UTC</span>
                        <span class="streaming-status text-[10px] text-primary animate-pulse">• Đang nhập...</span>
                    </div>
                    <div class="bg-surface-container/60 backdrop-blur-md p-5 rounded-2xl border-l-2 border-primary shadow-[0_4px_15px_rgba(0,0,0,0.15)] border border-white/[0.02]">
                        <div class="streaming-content"></div>
                        <span class="streaming-cursor animate-pulse">|</span>
                    </div>
                </div>
            </div>
        `;

        chatContainer.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }

    updateStreamingMessage(messageId, content) {
        // Update streaming message content progressively
        const messageElement = document.getElementById(messageId);
        if (!messageElement) return;

        const contentElement = messageElement.querySelector('.streaming-content');
        const statusElement = messageElement.querySelector('.streaming-status');
        const cursorElement = messageElement.querySelector('.streaming-cursor');

        if (contentElement) {
            // SECURE: Sanitize rendered markdown before setting innerHTML
            const renderedContent = this.renderMarkdown(content);
            if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
                CyberSecSanitizer.safeSetInnerHTML(contentElement, renderedContent);
            } else {
                contentElement.innerHTML = renderedContent; // Fallback if sanitizer not loaded
            }
        }

        // Update status text when content arrives
        if (statusElement && content && content.length > 0) {
            statusElement.textContent = '• Đang soạn thảo...';
        }

        this.scrollToBottom();

        // Remove cursor when complete
        if (cursorElement && content && content.length > 0 && !content.endsWith('|')) {
            cursorElement.style.display = 'none';
        }
    }

    finalizeStreamingMessage(messageId) {
        const messageElement = document.getElementById(messageId);
        if (!messageElement) return;

        const statusElement = messageElement.querySelector('.streaming-status');
        const cursorElement = messageElement.querySelector('.streaming-cursor');
        const iconElement = messageElement.querySelector('.streaming-icon');

        statusElement?.remove();
        cursorElement?.remove();
        iconElement?.classList.remove('animate-pulse');
    }

    renderMarkdown(text) {
        if (!text) return '';

        let html = this.escapeHtml(text);

        // 1. Parse Code Blocks: ```code```
        html = html.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<pre><code class="font-mono">${code.trim()}</code></pre>`;
        });

        // 2. Parse Inline Code: `code`
        html = html.replace(/`([^`\n]+)`/g, '<code class="font-mono bg-white/5 px-1 py-0.5 rounded text-xs text-primary-dim">$1</code>');

        // 3. Parse Bold: **text**
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 4. Parse Bullet Lists: lines starting with • or - or *
        const lines = html.split('\n');
        let inList = false;
        let listHTML = [];

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();
            if (line.startsWith('•') || line.startsWith('-') || line.startsWith('*')) {
                const cleanText = line.substring(1).trim();
                if (!inList) {
                    listHTML.push('<ul class="markdown-content">');
                    inList = true;
                }
                listHTML.push(`<li>${cleanText}</li>`);
            } else {
                if (inList) {
                    listHTML.push('</ul>');
                    inList = false;
                }
                listHTML.push(lines[i]);
            }
        }

        if (inList) {
            listHTML.push('</ul>');
        }

        html = listHTML.join('\n');

        // 5. Replace remaining newlines with <br/> (excluding inside pre blocks)
        const parts = html.split(/(<pre[\s\S]*?<\/pre>)/);
        for (let i = 0; i < parts.length; i++) {
            if (!parts[i].startsWith('<pre')) {
                parts[i] = parts[i].replace(/\n/g, '<br/>');
            }
        }
        html = parts.join('');

        // Defense in depth: Sanitize with DOMPurify to prevent XSS
        if (typeof DOMPurify !== 'undefined') {
            html = DOMPurify.sanitize(html);
        }

        return `<div class="markdown-content">${html}</div>`;
    }

    scrollToBottom() {
        const scrollContainer = document.getElementById('chatScrollContainer');
        if (scrollContainer) {
            scrollContainer.scrollTo({
                top: scrollContainer.scrollHeight,
                behavior: 'smooth'
            });
        }
    }

    escapeHtml(text) {
        return window.escapeHtml(text);
    }
}

// Initialize when DOM is ready and config is available
document.addEventListener('DOMContentLoaded', () => {
    if (window.chatControllerInitialized) {
        console.warn('⚠️ Chat controller already initialized, skipping duplicate initialization');
        return;
    }

    try {
        if (window.config) {
            console.log('✅ Config loaded, initializing chat controller');
            const chat = new ChatController();
            window.chatControllerInitialized = true;
        } else {
            console.warn('⚠️ Config not loaded, waiting...');
            setTimeout(() => {
                if (window.config && !window.chatControllerInitialized) {
                    console.log('✅ Config loaded after delay, initializing chat controller');
                    const chat = new ChatController();
                    window.chatControllerInitialized = true;
                } else {
                    console.error('❌ Config failed to load, chat cannot initialize');
                }
            }, 100);
        }
    } catch (error) {
        console.error('❌ Failed to initialize chat controller:', error);
    }
});
