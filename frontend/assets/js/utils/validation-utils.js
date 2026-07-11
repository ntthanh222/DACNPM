/**
 * Validation Utilities
 * Helper functions for input validation and security checks
 */

class ValidationUtils {
    /**
     * Validate email format
     * @param {string} email - Email to validate
     * @returns {boolean} Valid email
     */
    static isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate URL format
     * @param {string} url - URL to validate
     * @returns {boolean} Valid URL
     */
    static isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch (error) {
            return false;
        }
    }

    /**
     * Validate CVE ID format
     * @param {string} cveId - CVE ID to validate
     * @returns {boolean} Valid CVE ID
     */
    static isValidCveId(cveId) {
        const cveRegex = /^CVE-\d{4}-\d{4,7}$/i;
        return cveRegex.test(cveId);
    }

    /**
     * Validate password strength
     * @param {string} password - Password to validate
     * @returns {Object} Strength assessment
     */
    static validatePassword(password) {
        const result = {
            isValid: true,
            strength: 'weak',
            score: 0,
            issues: []
        };

        if (!password) {
            result.isValid = false;
            result.issues.push('Password is required');
            return result;
        }

        // Length check
        if (password.length < 8) {
            result.issues.push('Password must be at least 8 characters long');
        } else {
            result.score += 1;
        }

        // Uppercase check
        if (/[A-Z]/.test(password)) {
            result.score += 1;
        } else {
            result.issues.push('Password must contain at least one uppercase letter');
        }

        // Lowercase check
        if (/[a-z]/.test(password)) {
            result.score += 1;
        } else {
            result.issues.push('Password must contain at least one lowercase letter');
        }

        // Number check
        if (/[0-9]/.test(password)) {
            result.score += 1;
        } else {
            result.issues.push('Password must contain at least one number');
        }

        // Special character check
        if (/[^A-Za-z0-9]/.test(password)) {
            result.score += 1;
        } else {
            result.issues.push('Password must contain at least one special character');
        }

        // Determine strength
        if (result.score >= 4) {
            result.strength = 'strong';
        } else if (result.score >= 2) {
            result.strength = 'medium';
        } else {
            result.strength = 'weak';
            result.isValid = false;
        }

        return result;
    }

    /**
     * Sanitize user input to prevent XSS
     * @param {string} input - User input
     * @returns {string} Sanitized input
     */
    static sanitizeInput(input) {
        if (!input) return input;

        // Remove potentially dangerous HTML tags
        const dangerousTags = ['<script', '</script', '<iframe', '</iframe', '<object', '</object', '<embed', '</embed'];
        let sanitized = input;

        dangerousTags.forEach(tag => {
            const regex = new RegExp(tag, 'gi');
            sanitized = sanitized.replace(regex, '');
        });

        // Escape HTML entities
        const div = document.createElement('div');
        div.textContent = sanitized;
        return div.innerHTML;
    }

    /**
     * Validate and sanitize chat message
     * @param {string} message - Chat message
     * @returns {Object} Validation result
     */
    static validateChatMessage(message) {
        const result = {
            isValid: true,
            sanitized: '',
            error: null
        };

        if (!message || typeof message !== 'string') {
            result.isValid = false;
            result.error = 'Message is required';
            return result;
        }

        // Trim and check length
        const trimmed = message.trim();
        if (trimmed.length === 0) {
            result.isValid = false;
            result.error = 'Message cannot be empty';
            return result;
        }

        if (trimmed.length > 5000) {
            result.isValid = false;
            result.error = 'Message is too long (max 5000 characters)';
            return result;
        }

        // Sanitize
        result.sanitized = this.sanitizeInput(trimmed);
        return result;
    }

    /**
     * Validate news article data
     * @param {Object} newsData - News article data
     * @returns {Object} Validation result
     */
    static validateNewsData(newsData) {
        const result = {
            isValid: true,
            errors: []
        };

        if (!newsData.title || newsData.title.trim().length === 0) {
            result.errors.push('Title is required');
        }

        if (!newsData.summary || newsData.summary.trim().length === 0) {
            result.errors.push('Summary is required');
        }

        if (!newsData.url || !this.isValidUrl(newsData.url)) {
            result.errors.push('Valid URL is required');
        }

        if (!newsData.source || newsData.source.trim().length === 0) {
            result.errors.push('Source is required');
        }

        result.isValid = result.errors.length === 0;
        return result;
    }

    /**
     * Check for potential SQL injection patterns
     * @param {string} input - User input
     * @returns {boolean} Potentially malicious
     */
    static containsSqlInjection(input) {
        if (!input) return false;

        const sqlPatterns = [
            /(\bunion\b.*\bselect\b)/i,
            /(\bselect\b.*\bfrom\b)/i,
            /(\binsert\b.*\binto\b)/i,
            /(\bupdate\b.*\bset\b)/i,
            /(\bdelete\b.*\bfrom\b)/i,
            /(\bdrop\b.*\btable\b)/i,
            /(--)|(#)/,
            /(\/\*)|(\*\/)/
        ];

        return sqlPatterns.some(pattern => pattern.test(input));
    }

    /**
     * Check for potential XSS patterns
     * @param {string} input - User input
     * @returns {boolean} Potentially malicious
     */
    static containsXss(input) {
        if (!input) return false;

        const xssPatterns = [
            /<script[^>]*>.*?<\/script>/gi,
            /javascript:/gi,
            /onerror\s*=/gi,
            /onload\s*=/gi,
            /onclick\s*=/gi,
            /<iframe[^>]*>/gi
        ];

        return xssPatterns.some(pattern => pattern.test(input));
    }

    /**
     * Comprehensive security validation
     * @param {string} input - User input
     * @returns {Object} Security validation result
     */
    static securityCheck(input) {
        const result = {
            isSafe: true,
            sanitized: input,
            issues: []
        };

        if (!input) return result;

        if (this.containsSqlInjection(input)) {
            result.isSafe = false;
            result.issues.push('Potential SQL injection detected');
        }

        if (this.containsXss(input)) {
            result.isSafe = false;
            result.issues.push('Potential XSS attack detected');
        }

        if (result.isSafe) {
            result.sanitized = this.sanitizeInput(input);
        }

        return result;
    }
}

// Export to global scope
window.ValidationUtils = ValidationUtils;