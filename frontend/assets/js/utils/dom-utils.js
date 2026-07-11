/**
 * DOM Utilities
 * Helper functions for DOM manipulation
 */

class DOMUtils {
    /**
     * Escape HTML to prevent XSS attacks
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    static escapeHtml(text) {
        if (!text) return text;

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Format date to readable string
     * @param {Date|string} date - Date object or ISO string
     * @returns {string} Formatted date
     */
    static formatDate(date) {
        const d = new Date(date);
        return d.toLocaleString();
    }

    /**
     * Format date to time string
     * @param {Date|string} date - Date object or ISO string
     * @returns {string} Formatted time
     */
    static formatTime(date) {
        const d = date instanceof Date ? date : new Date(date);
        return d.toISOString().split('T')[1].split('.')[0] + ' UTC';
    }

    /**
     * Show element by ID
     * @param {string} elementId - Element ID
     */
    static showElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.remove('hidden');
        }
    }

    /**
     * Hide element by ID
     * @param {string} elementId - Element ID
     */
    static hideElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.add('hidden');
        }
    }

    /**
     * Toggle element visibility
     * @param {string} elementId - Element ID
     */
    static toggleElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.classList.toggle('hidden');
        }
    }

    /**
     * Set element content safely
     * @param {string} elementId - Element ID
     * @param {string} content - Content to set
     */
    static setElementContent(elementId, content) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = content;
        }
    }

    /**
     * Set element HTML safely
     * @param {string} elementId - Element ID
     * @param {string} html - HTML content
     */
    static setElementHTML(elementId, html) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = html;
        }
    }

    /**
     * Add event listener to element
     * @param {string} elementId - Element ID
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    static addEventListener(elementId, event, callback) {
        const element = document.getElementById(elementId);
        if (element) {
            element.addEventListener(event, callback);
        }
    }

    /**
     * Remove event listener from element
     * @param {string} elementId - Element ID
     * @param {string} event - Event name
     * @param {Function} callback - Event callback
     */
    static removeEventListener(elementId, event, callback) {
        const element = document.getElementById(elementId);
        if (element) {
            element.removeEventListener(event, callback);
        }
    }

    /**
     * Scroll element to bottom
     * @param {string} elementId - Element ID
     */
    static scrollToBottom(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollTop = element.scrollHeight;
        }
    }

    /**
     * Check if element exists
     * @param {string} elementId - Element ID
     * @returns {boolean} Element exists
     */
    static elementExists(elementId) {
        return document.getElementById(elementId) !== null;
    }

    /**
     * Get element value
     * @param {string} elementId - Element ID
     * @returns {string|null} Element value
     */
    static getElementValue(elementId) {
        const element = document.getElementById(elementId);
        return element ? element.value : null;
    }

    /**
     * Set element value
     * @param {string} elementId - Element ID
     * @param {string} value - Value to set
     */
    static setElementValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.value = value;
        }
    }
}

// Export to global scope
window.DOMUtils = DOMUtils;