/**
 * Stats Service
 * Handles all statistics and analytics API communication
 */

class StatsService {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
    }

    /**
     * Get vulnerability statistics
     * @returns {Promise<Object>} Vulnerability statistics
     */
    async getVulnerabilityStats() {
        const requestUrl = `${this.apiEndpoint}/api/stats/vulnerabilities`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Stats API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved vulnerability statistics');
            return data;

        } catch (error) {
            console.error('🔴 Stats API error:', error);
            throw error;
        }
    }

    /**
     * Get chat statistics
     * @returns {Promise<Object>} Chat statistics
     */
    async getChatStats() {
        const requestUrl = `${this.apiEndpoint}/api/stats/chat`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`Chat stats API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved chat statistics');
            return data;

        } catch (error) {
            console.error('🔴 Chat stats API error:', error);
            throw error;
        }
    }

    /**
     * Get system analytics (admin only)
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} System analytics
     */
    async getSystemAnalytics(token) {
        const requestUrl = `${this.apiEndpoint}/api/admin/system/analytics`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`System analytics API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved system analytics');
            return data;

        } catch (error) {
            console.error('🔴 System analytics API error:', error);
            throw error;
        }
    }

    /**
     * Get cached dashboard statistics (admin/analyst only)
     * @param {string} token - Authentication token
     * @param {boolean} forceRefresh - Force refresh of cache
     * @returns {Promise<Object>} Dashboard statistics
     */
    async getDashboardStats(token, forceRefresh = false) {
        const requestUrl = `${this.apiEndpoint}/api/admin/system/dashboard/cached?force_refresh=${forceRefresh}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Dashboard stats API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved dashboard statistics');
            return data;

        } catch (error) {
            console.error('🔴 Dashboard stats API error:', error);
            throw error;
        }
    }

    /**
     * Get API usage statistics (admin/analyst only)
     * @param {string} token - Authentication token
     * @param {number} days - Number of days to retrieve
     * @returns {Promise<Object>} API usage statistics
     */
    async getApiUsage(token, days = 30) {
        const requestUrl = `${this.apiEndpoint}/api/admin/system/api-usage?days=${days}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`API usage stats failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved API usage statistics');
            return data;

        } catch (error) {
            console.error('🔴 API usage stats error:', error);
            throw error;
        }
    }

    /**
     * Get CVE lookup cache statistics (admin/analyst only)
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} CVE cache statistics
     */
    async getCveCacheStats(token) {
        const requestUrl = `${this.apiEndpoint}/api/admin/system/cache`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`CVE cache stats API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved CVE cache statistics');
            return data;

        } catch (error) {
            console.error('🔴 CVE cache stats error:', error);
            throw error;
        }
    }
}

// Export singleton instance
window.statsService = new StatsService();