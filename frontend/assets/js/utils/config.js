/**
 * Configuration Manager
 * Loads system configuration from multiple sources
 */
class ConfigManager {
    constructor() {
        this.config = this.loadConfig();
    }

    loadConfig() {
        // Try to load from global config object (if injected by build process)
        if (window.APP_CONFIG) {
            return {
                ...window.APP_CONFIG,
                chatbotEndpoint: this.normalizeChatbotEndpoint(window.APP_CONFIG.chatbotEndpoint)
            };
        }

        // Fallback: detect environment
        const isDevelopment = window.location.hostname === 'localhost' ||
                            window.location.hostname === '127.0.0.1';

        // Use current origin for proper proxy/domain support
        const origin = window.location.origin;

        // Default configuration for development
        return {
            chatbotEndpoint: this.normalizeChatbotEndpoint(`${origin}/api/chatbot`),
            apiEndpoint: origin,
            phishingCheckEndpoint: `${origin}/api/chatbot/phishing-check`,
            passwordStrengthEndpoint: `${origin}/api/chatbot/password-strength`,
            newsLimit: 10,
            isDevelopment: isDevelopment,
            debug: isDevelopment
        };
    }

    normalizeChatbotEndpoint(endpoint) {
        if (!endpoint || typeof endpoint !== 'string') {
            return endpoint;
        }

        return endpoint.replace(/\/+$/, '').replace(/\/chat$/, '');
    }

    get(key) {
        return this.config[key];
    }

    set(key, value) {
        this.config[key] = value;
    }

    // Allow dynamic override for testing
    override(newConfig) {
        this.config = { ...this.config, ...newConfig };
        console.log('Configuration overridden:', this.config);
    }

    // Get all configuration (useful for debugging)
    getAll() {
        return { ...this.config };
    }
}

// Export singleton instance
window.config = new ConfigManager();

// Log configuration in development mode
if (window.config.get('debug')) {
    console.log('🔧 Configuration loaded:', window.config.getAll());
}
