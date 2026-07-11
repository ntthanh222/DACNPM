/**
 * News Service
 * Handles all security news API communication
 */

class NewsService {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
    }

    /**
     * Get latest security news
     * @param {number} limit - Maximum number of news items to return
     * @param {string} source - Optional source filter
     * @returns {Promise<Array>} Security news items
     */
    async getLatestNews(limit = 10, source = null) {
        const requestUrl = `${this.apiEndpoint}/api/news/latest?limit=${limit}${source ? '&source=' + encodeURIComponent(source) : ''}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`News API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`✅ Retrieved ${data.length} news items`);
            return data;

        } catch (error) {
            console.error('🔴 News API error:', error);
            throw error;
        }
    }

    /**
     * Get all security news with pagination
     * @param {number} limit - Maximum number of news items
     * @param {string} source - Optional source filter
     * @returns {Promise<Array>} Security news items
     */
    async getAllNews(limit = 50, source = null) {
        const requestUrl = `${this.apiEndpoint}/api/news/?limit=${limit}${source ? '&source=' + encodeURIComponent(source) : ''}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`News API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log(`✅ Retrieved ${data.length} news items`);
            return data;

        } catch (error) {
            console.error('🔴 News API error:', error);
            throw error;
        }
    }

    /**
     * Get specific news item by ID
     * @param {string} newsId - News item ID
     * @returns {Promise<Object>} News item
     */
    async getNewsById(newsId) {
        const requestUrl = `${this.apiEndpoint}/api/news/${newsId}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('News item not found');
                }
                throw new Error(`News API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved news item:', data);
            return data;

        } catch (error) {
            console.error('🔴 News API error:', error);
            throw error;
        }
    }

    /**
     * Create new news item (requires admin/analyst role)
     * @param {Object} newsData - News item data
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} Created news item
     */
    async createNews(newsData, token) {
        const requestUrl = `${this.apiEndpoint}/api/news/`;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(newsData)
            });

            if (!response.ok) {
                throw new Error(`Create news API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ News item created successfully');
            return data;

        } catch (error) {
            console.error('🔴 Create news error:', error);
            throw error;
        }
    }

    /**
     * Update news item (requires admin/analyst role)
     * @param {string} newsId - News item ID
     * @param {Object} newsData - Updated news data
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} Updated news item
     */
    async updateNews(newsId, newsData, token) {
        const requestUrl = `${this.apiEndpoint}/api/news/${newsId}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(newsData)
            });

            if (!response.ok) {
                throw new Error(`Update news API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ News item updated successfully');
            return data;

        } catch (error) {
            console.error('🔴 Update news error:', error);
            throw error;
        }
    }

    /**
     * Delete news item (requires admin/analyst role)
     * @param {string} newsId - News item ID
     * @param {string} token - Authentication token
     * @returns {Promise<boolean>} Success status
     */
    async deleteNews(newsId, token) {
        const requestUrl = `${this.apiEndpoint}/api/news/${newsId}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`Delete news API failed: ${response.status} ${response.statusText}`);
            }

            console.log('✅ News item deleted successfully');
            return true;

        } catch (error) {
            console.error('🔴 Delete news error:', error);
            throw error;
        }
    }
}

// Export singleton instance
window.newsService = new NewsService();