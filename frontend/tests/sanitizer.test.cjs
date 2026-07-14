const assert = require('node:assert/strict');
const test = require('node:test');

// Mock window and DOMPurify for the test
global.DOMPurify = {
    sanitize(html, config) {
        // Simple mock of DOMPurify sanitization
        if (html.includes('<script>')) {
            return html.replace(/<script>.*?<\/script>/g, '');
        }
        return html;
    },
    addHook(name, callback) {
        this.hookName = name;
        this.hookCallback = callback;
    }
};

global.document = {
    createElement(tag) {
        return {
            tagName: tag,
            textContent: '',
            get innerHTML() {
                // simple escape logic
                return this.textContent
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#039;');
            }
        };
    }
};

const sanitizer = require('../assets/js/utils/sanitizer.js');

test('sanitizer.basicEscapeHtml - escapes HTML special characters', () => {
    const raw = '<script>alert("XSS")</script> & some other text';
    const escaped = sanitizer.basicEscapeHtml(raw);
    assert.equal(escaped, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt; &amp; some other text');
});

test('sanitizer.sanitizeHTML - utilizes DOMPurify and handles null/empty/invalid', () => {
    // Happy path
    assert.equal(sanitizer.sanitizeHTML('<b>hello</b>'), '<b>hello</b>');
    // Null/undefined boundaries
    assert.equal(sanitizer.sanitizeHTML(null), '');
    assert.equal(sanitizer.sanitizeHTML(undefined), '');
    assert.equal(sanitizer.sanitizeHTML(123), ''); // Non-string boundary

    // XSS sanitization
    assert.equal(sanitizer.sanitizeHTML('<script>alert(1)</script>hello'), 'hello');
});

test('sanitizer.safeClearContent - removes all children from element', () => {
    const children = [{ name: 'child1' }, { name: 'child2' }];
    const element = {
        get firstChild() {
            return children.length > 0 ? children[0] : null;
        },
        removeChild(child) {
            const index = children.indexOf(child);
            if (index > -1) {
                children.splice(index, 1);
            }
        }
    };

    sanitizer.safeClearContent(element);
    assert.equal(children.length, 0);
});
