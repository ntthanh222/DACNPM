/**
 * Shared utility functions for CyberSec Assistant
 *
 * This module consolidates common utility functions used across multiple
 * JavaScript files to avoid code duplication and ensure consistency.
 */

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - The text to escape
 * @returns {string} - The escaped HTML string
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Generate UUID v4
 * @returns {string} - A random UUID v4 string
 */
function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Get or create user ID from localStorage
 * Generates a new UUID if no user ID exists
 * @returns {string} - The user ID
 */
function getOrCreateUserId() {
    let userId = localStorage.getItem('cybersec_user_id');
    if (!userId) {
        userId = generateUUID();
        localStorage.setItem('cybersec_user_id', userId);
    }
    return userId;
}

/**
 * Format date for display
 * @param {string|Date} date - The date to format
 * @returns {string} - Formatted date string
 */
function formatDate(date) {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('vi-VN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

/**
 * Format relative time (e.g., "2 hours ago")
 * @param {string|Date} date - The date to format
 * @returns {string} - Relative time string
 */
function formatRelativeTime(date) {
    if (!date) return '';
    const d = new Date(date);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins} phút trước`;
    if (diffHours < 24) return `${diffHours} giờ trước`;
    if (diffDays < 7) return `${diffDays} ngày trước`;
    return formatDate(date);
}

/**
 * Debounce function to limit execution rate
 * @param {Function} func - The function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Deep clone an object
 * @param {any} obj - The object to clone
 * @returns {any} - The cloned object
 */
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));

    const clonedObj = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            clonedObj[key] = deepClone(obj[key]);
        }
    }
    return clonedObj;
}

/**
 * Safe JSON parse with fallback
 * @param {string} json - The JSON string to parse
 * @param {any} fallback - Fallback value if parsing fails
 * @returns {any} - Parsed object or fallback
 */
function safeJSONParse(json, fallback = null) {
    try {
        return JSON.parse(json);
    } catch (e) {
        console.warn('JSON parse error:', e);
        return fallback;
    }
}

/**
 * Check if code is running in development mode
 * @returns {boolean} - True if in development mode
 */
function isDevelopment() {
    return window.location.hostname === 'localhost' ||
           window.location.hostname === '127.0.0.1' ||
           window.location.hostname === '';
}

/**
 * Log to console only in development
 * @param {...any} args - Arguments to log
 */
function devLog(...args) {
    if (isDevelopment()) {
        console.log('[Dev]', ...args);
    }
}

/**
 * Truncate text to specified length
 * @param {string} text - The text to truncate
 * @param {number} maxLength - Maximum length
 * @param {string} suffix - Suffix to add (default: '...')
 * @returns {string} - Truncated text
 */
function truncateText(text, maxLength, suffix = '...') {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength - suffix.length) + suffix;
}

/**
 * Capitalize first letter of string
 * @param {string} str - The string to capitalize
 * @returns {string} - Capitalized string
 */
function capitalize(str) {
    if (!str) return '';
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Convert severity level to color
 * @param {string} severity - Severity level (low, medium, high, critical)
 * @returns {string} - CSS color class or hex code
 */
function severityToColor(severity) {
    const colors = {
        'none': '#4caf50',
        'low': '#8bc34a',
        'medium': '#ff9800',
        'high': '#f44336',
        'critical': '#d32f2f'
    };
    return colors[severity?.toLowerCase()] || '#757575';
}

/**
 * Check if element is in viewport
 * @param {Element} element - The element to check
 * @returns {boolean} - True if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Smooth scroll to element
 * @param {Element|string} target - Element or selector to scroll to
 * @param {Object} options - Scroll options
 */
function scrollToElement(target, options = {}) {
    const element = typeof target === 'string' ?
        document.querySelector(target) : target;

    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'start',
            ...options
        });
    }
}

// Expose functions to window for global access
window.escapeHtml = escapeHtml;
window.generateUUID = generateUUID;
window.getOrCreateUserId = getOrCreateUserId;
window.formatDate = formatDate;
window.formatRelativeTime = formatRelativeTime;
window.debounce = debounce;
window.deepClone = deepClone;
window.safeJSONParse = safeJSONParse;
window.isDevelopment = isDevelopment;
window.devLog = devLog;
window.truncateText = truncateText;
window.capitalize = capitalize;
window.severityToColor = severityToColor;
window.isInViewport = isInViewport;
window.scrollToElement = scrollToElement;

// Export utilities for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        escapeHtml,
        generateUUID,
        getOrCreateUserId,
        formatDate,
        formatRelativeTime,
        debounce,
        deepClone,
        safeJSONParse,
        isDevelopment,
        devLog,
        truncateText,
        capitalize,
        severityToColor,
        isInViewport,
        scrollToElement
    };
}