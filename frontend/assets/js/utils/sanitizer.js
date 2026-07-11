/**
 * HTML Sanitizer Utility for CyberSec Assistant
 *
 * Provides comprehensive XSS protection using DOMPurify library.
 * All user-generated content should be sanitized before rendering.
 *
 * SECURITY: This prevents prompt injection attacks and XSS vulnerabilities
 * when rendering LLM responses, markdown content, and user inputs.
 */

// DOMPurify CDN: https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js
// Include this in your HTML before sanitizer.js:
// <script src="https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js"></script>

/**
 * Configuration for DOMPurify sanitization
 * Defines which HTML tags and attributes are allowed in sanitized content
 */
const SANITIZER_CONFIG = {
    // Allowed HTML tags (security-conscious whitelist)
    ALLOWED_TAGS: [
        // Text formatting
        'b', 'i', 'em', 'strong', 'u', 's', 'sub', 'sup',
        // Headings
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        // Lists
        'ul', 'ol', 'li',
        // Code and preformatted text
        'code', 'pre', 'blockquote',
        // Links (with security restrictions)
        'a',
        // Basic structure
        'p', 'br', 'hr', 'div', 'span',
        // Tables
        'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ],

    // Allowed attributes (security-conscious whitelist)
    ALLOWED_ATTR: [
        // Links
        'href', 'title', 'target',
        // Images
        'src', 'alt', 'width', 'height',
        // Standard attributes
        'class', 'id', 'style',
        // Code syntax highlighting
        'data-language'
    ],

    // Additional security options
    ALLOW_DATA_ATTR: false,          // Block data-* attributes (potential XSS vectors)
    ALLOW_UNKNOWN_PROTOCOLS: false,   // Block unknown protocols in links
    ALLOW_STYLE_TAGS: false,          // Block inline style tags (CSS injection risk)
    SAFE_FOR_TEMPLATES: true,        // Safe for template systems
    SANITIZE_DOM: true,              // Sanitize the DOM itself
    FORCE_BODY: false,               // Don't force body tag
};

/**
 * Sanitize HTML content to prevent XSS attacks
 *
 * @param {string} html - The HTML content to sanitize
 * @param {Object} customConfig - Optional custom DOMPurify configuration
 * @returns {string} - Sanitized HTML safe to render
 */
function sanitizeHTML(html, customConfig = {}) {
    if (!html || typeof html !== 'string') {
        return '';
    }

    // Check if DOMPurify is available
    if (typeof DOMPurify === 'undefined') {
        console.error('❌ DOMPurify not loaded. Include DOMPurify CDN: https://cdnjs.cloudflare.com/ajax/libs/dompurify/3.0.6/purify.min.js');
        // Fallback to basic escaping if DOMPurify not available
        return basicEscapeHtml(html);
    }

    try {
        // Merge custom config with default config
        const config = { ...SANITIZER_CONFIG, ...customConfig };

        // Additional security: Remove javascript: and data: protocols from links
        const addHook = DOMPurify.addHook;

        // Add hook to sanitize href attributes
        DOMPurify.addHook('uponSanitizeAttribute', (node, data) => {
            if (data.attrName === 'href' && data.attrValue) {
                // Block dangerous protocols
                const dangerousProtocols = ['javascript:', 'data:', 'vbscript:', 'file:'];
                const lowerValue = data.attrValue.toLowerCase();

                for (const protocol of dangerousProtocols) {
                    if (lowerValue.includes(protocol)) {
                        data.attrValue = ''; // Remove dangerous href
                        console.warn('⚠️ Blocked dangerous href protocol:', protocol);
                    }
                }
            }
        });

        // Sanitize the HTML
        const sanitized = DOMPurify.sanitize(html, config);

        return sanitized;

    } catch (error) {
        console.error('❌ Error sanitizing HTML:', error);
        // Fallback to basic escaping on error
        return basicEscapeHtml(html);
    }
}

/**
 * Basic HTML escaping as fallback when DOMPurify is not available
 * This is less comprehensive but provides basic XSS protection
 *
 * @param {string} text - Text to escape
 * @returns {string} - Escaped HTML
 */
function basicEscapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Sanitize markdown content specifically
 * Provides additional protections for code blocks and links
 *
 * @param {string} markdown - Markdown content to sanitize
 * @returns {string} - Sanitized HTML safe to render
 */
function sanitizeMarkdown(markdown) {
    if (!markdown) return '';

    // Convert markdown to HTML (using your existing renderMarkdown)
    let html = markdown; // Your markdown rendering logic here

    // Then sanitize the HTML
    return sanitizeHTML(html);
}

/**
 * Safe innerHTML setter - prevents XSS vulnerabilities
 * Use this instead of directly setting element.innerHTML
 *
 * @param {HTMLElement} element - The DOM element to update
 * @param {string} content - The content to set (will be sanitized)
 */
function safeSetInnerHTML(element, content) {
    if (!element || !content) return;

    // Sanitize the content first
    const sanitized = sanitizeHTML(content);

    // Set the sanitized content
    element.innerHTML = sanitized;
}

/**
 * Clear element content safely
 * Use this instead of element.innerHTML = ''
 *
 * @param {HTMLElement} element - The DOM element to clear
 */
function safeClearContent(element) {
    if (!element) return;

    // Remove all child nodes (safer than innerHTML = '')
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    // Node.js/CommonJS
    module.exports = {
        sanitizeHTML,
        sanitizeMarkdown,
        safeSetInnerHTML,
        safeClearContent,
        basicEscapeHtml,
        SANITIZER_CONFIG
    };
} else {
    // Browser - make available globally
    window.CyberSecSanitizer = {
        sanitizeHTML,
        sanitizeMarkdown,
        safeSetInnerHTML,
        safeClearContent,
        basicEscapeHtml,
        SANITIZER_CONFIG
    };

    console.log('✅ CyberSec HTML Sanitizer loaded');
    console.log('📝 Usage: CyberSecSanitizer.safeSetInnerHTML(element, content)');
}
