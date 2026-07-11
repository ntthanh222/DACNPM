/**
 * Storage Utilities
 * Helper functions for localStorage and sessionStorage management
 */

class StorageUtils {
    /**
     * Set item in localStorage with error handling
     * @param {string} key - Storage key
     * @param {any} value - Value to store
     * @returns {boolean} Success status
     */
    static setLocalItem(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('localStorage set error:', error);
            return false;
        }
    }

    /**
     * Get item from localStorage with error handling
     * @param {string} key - Storage key
     * @param {any} defaultValue - Default value if key doesn't exist
     * @returns {any} Stored value or default
     */
    static getLocalItem(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('localStorage get error:', error);
            return defaultValue;
        }
    }

    /**
     * Remove item from localStorage
     * @param {string} key - Storage key
     * @returns {boolean} Success status
     */
    static removeLocalItem(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('localStorage remove error:', error);
            return false;
        }
    }

    /**
     * Clear all localStorage items
     * @returns {boolean} Success status
     */
    static clearLocal() {
        try {
            localStorage.clear();
            return true;
        } catch (error) {
            console.error('localStorage clear error:', error);
            return false;
        }
    }

    /**
     * Set item in sessionStorage with error handling
     * @param {string} key - Storage key
     * @param {any} value - Value to store
     * @returns {boolean} Success status
     */
    static setSessionItem(key, value) {
        try {
            sessionStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (error) {
            console.error('sessionStorage set error:', error);
            return false;
        }
    }

    /**
     * Get item from sessionStorage with error handling
     * @param {string} key - Storage key
     * @param {any} defaultValue - Default value if key doesn't exist
     * @returns {any} Stored value or default
     */
    static getSessionItem(key, defaultValue = null) {
        try {
            const item = sessionStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('sessionStorage get error:', error);
            return defaultValue;
        }
    }

    /**
     * Remove item from sessionStorage
     * @param {string} key - Storage key
     * @returns {boolean} Success status
     */
    static removeSessionItem(key) {
        try {
            sessionStorage.removeItem(key);
            return true;
        } catch (error) {
            console.error('sessionStorage remove error:', error);
            return false;
        }
    }

    /**
     * Clear all sessionStorage items
     * @returns {boolean} Success status
     */
    static clearSession() {
        try {
            sessionStorage.clear();
            return true;
        } catch (error) {
            console.error('sessionStorage clear error:', error);
            return false;
        }
    }

    /**
     * Get all localStorage keys
     * @returns {Array<string>} All keys
     */
    static getLocalKeys() {
        try {
            return Object.keys(localStorage);
        } catch (error) {
            console.error('localStorage get keys error:', error);
            return [];
        }
    }

    /**
     * Get all sessionStorage keys
     * @returns {Array<string>} All keys
     */
    static getSessionKeys() {
        try {
            return Object.keys(sessionStorage);
        } catch (error) {
            console.error('sessionStorage get keys error:', error);
            return [];
        }
    }

    /**
     * Check if localStorage has item
     * @param {string} key - Storage key
     * @returns {boolean} Item exists
     */
    static hasLocalItem(key) {
        return localStorage.getItem(key) !== null;
    }

    /**
     * Check if sessionStorage has item
     * @param {string} key - Storage key
     * @returns {boolean} Item exists
     */
    static hasSessionItem(key) {
        return sessionStorage.getItem(key) !== null;
    }

    /**
     * Get storage size (in bytes)
     * @param {boolean} session - Use sessionStorage instead of localStorage
     * @returns {number} Storage size
     */
    static getStorageSize(session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            let total = 0;

            for (const key in storage) {
                if (storage.hasOwnProperty(key)) {
                    total += storage[key].length + key.length;
                }
            }

            return total;
        } catch (error) {
            console.error('Storage size calculation error:', error);
            return 0;
        }
    }

    /**
     * Format storage size to human readable
     * @param {number} bytes - Size in bytes
     * @returns {string} Formatted size
     */
    static formatStorageSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
        return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
    }

    /**
     * Clean old items from storage
     * @param {number} maxAge - Maximum age in milliseconds
     * @param {boolean} session - Use sessionStorage instead of localStorage
     * @returns {number} Number of items removed
     */
    static cleanOldItems(maxAge = 7 * 24 * 60 * 60 * 1000, session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            const now = Date.now();
            let removed = 0;

            for (const key in storage) {
                if (storage.hasOwnProperty(key)) {
                    try {
                        const item = JSON.parse(storage[key]);
                        if (item.timestamp && (now - item.timestamp) > maxAge) {
                            storage.removeItem(key);
                            removed++;
                        }
                    } catch (parseError) {
                        // Skip items that can't be parsed
                        continue;
                    }
                }
            }

            return removed;
        } catch (error) {
            console.error('Clean old items error:', error);
            return 0;
        }
    }

    /**
     * Export storage data
     * @param {boolean} session - Use sessionStorage instead of localStorage
     * @returns {Object} All storage data
     */
    static exportStorage(session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;
            const data = {};

            for (const key in storage) {
                if (storage.hasOwnProperty(key)) {
                    try {
                        data[key] = JSON.parse(storage[key]);
                    } catch (parseError) {
                        data[key] = storage[key];
                    }
                }
            }

            return data;
        } catch (error) {
            console.error('Export storage error:', error);
            return {};
        }
    }

    /**
     * Import storage data
     * @param {Object} data - Data to import
     * @param {boolean} session - Use sessionStorage instead of localStorage
     * @returns {boolean} Success status
     */
    static importStorage(data, session = false) {
        try {
            const storage = session ? sessionStorage : localStorage;

            for (const key in data) {
                if (data.hasOwnProperty(key)) {
                    storage.setItem(key, JSON.stringify(data[key]));
                }
            }

            return true;
        } catch (error) {
            console.error('Import storage error:', error);
            return false;
        }
    }
}

// Export to global scope
window.StorageUtils = StorageUtils;