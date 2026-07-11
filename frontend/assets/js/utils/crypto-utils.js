/**
 * Crypto Utilities
 * Provides AES-GCM encryption for sensitive data (JWT tokens, etc.)
 * Fallback to Base64 encoding for browsers without Web Crypto API support
 */
class CryptoUtils {
    /**
     * Generate encryption key from secret using PBKDF2
     * @param {string} secret - The secret to derive key from
     * @returns {Promise<CryptoKey>} Derived encryption key
     */
    static async generateKey(secret) {
        try {
            const encoder = new TextEncoder();
            const keyMaterial = await crypto.subtle.importKey(
                'raw',
                encoder.encode(secret),
                'PBKDF2',
                false,
                ['deriveKey']
            );

            return crypto.subtle.deriveKey(
                {
                    name: 'PBKDF2',
                    salt: encoder.encode('cybersec-salt'),
                    iterations: 100000,
                    hash: 'SHA-256'
                },
                keyMaterial,
                { name: 'AES-GCM', length: 256 },
                false,
                ['encrypt', 'decrypt']
            );
        } catch (error) {
            console.error('Key generation error:', error);
            throw new Error('Failed to generate encryption key');
        }
    }

    /**
     * Encrypt data using AES-GCM
     * @param {string} data - Data to encrypt
     * @param {string} secret - Encryption secret
     * @returns {Promise<string|null>} Base64 encoded encrypted data or null on failure
     */
    static async encrypt(data, secret) {
        try {
            const key = await this.generateKey(secret);
            const encoder = new TextEncoder();
            const iv = crypto.getRandomValues(new Uint8Array(12));

            const encrypted = await crypto.subtle.encrypt(
                { name: 'AES-GCM', iv: iv },
                key,
                encoder.encode(data)
            );

            // Combine IV and encrypted data
            const combined = new Uint8Array(iv.length + encrypted.byteLength);
            combined.set(iv);
            combined.set(new Uint8Array(encrypted), iv.length);

            // Return as Base64
            return btoa(String.fromCharCode(...combined));
        } catch (error) {
            console.error('Encryption error:', error);
            return null;
        }
    }

    /**
     * Decrypt data using AES-GCM
     * @param {string} encryptedData - Base64 encoded encrypted data
     * @param {string} secret - Decryption secret
     * @returns {Promise<string|null>} Decrypted data or null on failure
     */
    static async decrypt(encryptedData, secret) {
        try {
            const key = await this.generateKey(secret);
            const combined = Uint8Array.from(atob(encryptedData), c => c.charCodeAt(0));

            // Extract IV and encrypted data
            const iv = combined.slice(0, 12);
            const encrypted = combined.slice(12);

            const decrypted = await crypto.subtle.decrypt(
                { name: 'AES-GCM', iv: iv },
                key,
                encrypted
            );

            const decoder = new TextDecoder();
            return decoder.decode(decrypted);
        } catch (error) {
            console.error('Decryption error:', error);
            return null;
        }
    }

    /**
     * Fallback: Simple Base64 encoding (not secure, but better than nothing)
     * Used when Web Crypto API is not available
     * @param {string} data - Data to encode
     * @returns {string} Base64 encoded data
     */
    static encodeBase64(data) {
        try {
            return btoa(data);
        } catch (error) {
            console.error('Base64 encoding error:', error);
            return data;
        }
    }

    /**
     * Fallback: Simple Base64 decoding
     * Used when Web Crypto API is not available
     * @param {string} encodedData - Base64 encoded data
     * @returns {string} Decoded data
     */
    static decodeBase64(encodedData) {
        try {
            return atob(encodedData);
        } catch (error) {
            console.error('Base64 decoding error:', error);
            return encodedData;
        }
    }

    /**
     * Check if Web Crypto API is available
     * @returns {boolean} True if Web Crypto API is available
     */
    static isCryptoAvailable() {
        return typeof crypto !== 'undefined' &&
               crypto.subtle &&
               typeof Promise !== 'undefined';
    }

    /**
     * Generate random encryption secret
     * @returns {string} Random 64-character hex string
     */
    static generateSecret() {
        try {
            if (this.isCryptoAvailable()) {
                const bytes = crypto.getRandomValues(new Uint8Array(32));
                return Array.from(bytes)
                    .map(b => b.toString(16).padStart(2, '0'))
                    .join('');
            }
        } catch (error) {
            console.warn('Crypto getRandomValues failed, using fallback:', error);
        }

        // Fallback: Math.random (less secure)
        return Array.from({ length: 32 }, () =>
            Math.floor(Math.random() * 256).toString(16).padStart(2, '0')
        ).join('');
    }
}

// Export to global scope
window.CryptoUtils = CryptoUtils;
