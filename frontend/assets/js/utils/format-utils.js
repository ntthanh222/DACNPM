/**
 * Format Utilities
 * Helper functions for formatting and displaying data
 */

class FormatUtils {
    /**
     * Format bytes to human readable size
     * @param {number} bytes - Number of bytes
     * @param {number} decimals - Number of decimal places
     * @returns {string} Formatted size
     */
    static formatBytes(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }

    /**
     * Format number with commas
     * @param {number} num - Number to format
     * @returns {string} Formatted number
     */
    static formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    /**
     * Format percentage
     * @param {number} value - Value
     * @param {number} total - Total
     * @param {number} decimals - Decimal places
     * @returns {string} Formatted percentage
     */
    static formatPercentage(value, total, decimals = 1) {
        if (total === 0) return '0%';
        const percentage = (value / total) * 100;
        return percentage.toFixed(decimals) + '%';
    }

    /**
     * Format date to relative time
     * @param {Date|string} date - Date to format
     * @returns {string} Relative time string
     */
    static formatRelativeTime(date) {
        const d = new Date(date);
        const now = new Date();
        const diffMs = now - d;
        const diffSecs = Math.floor(diffMs / 1000);
        const diffMins = Math.floor(diffSecs / 60);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffSecs < 60) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return d.toLocaleDateString();
    }

    /**
     * Truncate text to specified length
     * @param {string} text - Text to truncate
     * @param {number} maxLength - Maximum length
     * @param {string} suffix - Suffix to add (default: '...')
     * @returns {string} Truncated text
     */
    static truncateText(text, maxLength, suffix = '...') {
        if (!text || text.length <= maxLength) return text;
        return text.substring(0, maxLength - suffix.length) + suffix;
    }

    /**
     * Format CVSS score to severity level
     * @param {number} score - CVSS score
     * @returns {string} Severity level
     */
    static cvssToSeverity(score) {
        if (score >= 9.0) return 'critical';
        if (score >= 7.0) return 'high';
        if (score >= 4.0) return 'medium';
        if (score > 0) return 'low';
        return 'info';
    }

    /**
     * Get severity color class
     * @param {string} severity - Severity level
     * @returns {string} CSS color class
     */
    static getSeverityColor(severity) {
        const colors = {
            'critical': 'text-error',
            'high': 'text-warning',
            'medium': 'text-info',
            'low': 'text-success',
            'info': 'text-outline'
        };
        return colors[severity.toLowerCase()] || 'text-outline';
    }

    /**
     * Format chat confidence score
     * @param {number} confidence - Confidence score (0-1)
     * @returns {string} Formatted confidence percentage
     */
    static formatConfidence(confidence) {
        return Math.round(confidence * 100) + '%';
    }

    /**
     * Clean and format intent name
     * @param {string} intent - Intent name
     * @returns {string} Formatted intent name
     */
    static formatIntent(intent) {
        if (!intent) return 'Unknown';
        return intent
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    /**
     * Format source name for display
     * @param {string} source - Source name
     * @returns {string} Formatted source name
     */
    static formatSource(source) {
        if (!source) return 'Unknown';
        return source
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');
    }

    /**
     * Generate message ID
     * @returns {string} Unique message ID
     */
    static generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Safe JSON stringify
     * @param {Object} obj - Object to stringify
     * @returns {string} JSON string
     */
    static safeStringify(obj) {
        try {
            return JSON.stringify(obj);
        } catch (error) {
            console.error('JSON stringify error:', error);
            return '{}';
        }
    }

    /**
     * Safe JSON parse
     * @param {string} str - JSON string
     * @returns {Object|null} Parsed object or null
     */
    static safeParse(str) {
        try {
            return JSON.parse(str);
        } catch (error) {
            console.error('JSON parse error:', error);
            return null;
        }
    }
}

// Export to global scope
window.FormatUtils = FormatUtils;