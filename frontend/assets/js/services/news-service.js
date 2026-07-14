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

    escapeHTML(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    formatPublishedDate(value) {
        if (!value) return 'Unknown time';

        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Unknown time';

        return date.toLocaleDateString('vi-VN', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    getNewsDescription(item) {
        return item.description || item.summary || 'No summary available.';
    }

    generateNewsCards(newsItems, detailed = false) {
        if (!Array.isArray(newsItems) || newsItems.length === 0) {
            return `
                <div class="text-center text-on-surface-variant py-8">
                    <p>No security news available.</p>
                </div>
            `;
        }

        return newsItems.map((item) => {
            const title = this.escapeHTML(item.title || 'Untitled security update');
            const source = this.escapeHTML(item.source || 'Unknown source');
            const description = this.escapeHTML(this.getNewsDescription(item));
            const publishedAt = this.escapeHTML(this.formatPublishedDate(item.published_at || item.created_at));
            const url = this.escapeHTML(item.url || '#');
            const cardPadding = detailed ? 'p-6' : 'p-4';
            const descriptionClass = detailed ? 'line-clamp-3' : 'line-clamp-2';

            return `
                <article class="bg-surface-container border border-outline-variant/20 rounded-xl ${cardPadding} hover:border-primary/30 transition-colors">
                    <div class="flex items-start justify-between gap-4 mb-3">
                        <div class="min-w-0">
                            <p class="text-[10px] font-headline tracking-widest uppercase text-primary mb-2">${source}</p>
                            <h4 class="font-headline font-bold text-on-surface leading-snug">${title}</h4>
                        </div>
                        <span class="shrink-0 text-[10px] font-mono text-on-surface-variant">${publishedAt}</span>
                    </div>
                    <p class="text-sm text-on-surface-variant ${descriptionClass} mb-4">${description}</p>
                    <a class="inline-flex items-center gap-2 text-xs font-headline tracking-widest uppercase text-primary hover:text-on-surface transition-colors" href="${url}" target="_blank" rel="noopener noreferrer">
                        Read source
                        <span class="material-symbols-outlined text-sm" aria-hidden="true">open_in_new</span>
                    </a>
                </article>
            `;
        }).join('');
    }

    async loadAndDisplayNews(containerId, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`News container not found: ${containerId}`);
        }

        const limit = options.limit || 10;
        const newsItems = options.showLatest
            ? await this.getLatestNews(limit, options.source || null)
            : await this.getAllNews(limit, options.source || null);
        const html = this.generateNewsCards(newsItems, Boolean(options.detailed));

        if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
            CyberSecSanitizer.safeSetInnerHTML(container, html);
        } else {
            container.innerHTML = html;
        }

        return newsItems;
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
