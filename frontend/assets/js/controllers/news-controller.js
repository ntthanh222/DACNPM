/**
 * News Controller
 * Handles news functionality for the dashboard
 * Manages security news loading and display
 */
class NewsController {
    constructor(userId, apiEndpoint) {
        this.userId = userId;
        this.apiEndpoint = apiEndpoint;
        this.newsLimit = 3;

        // UI elements
        this.ui = {
            container: document.getElementById('newsContainer')
        };

        // Cleanup state tracking
        this.isCleanedUp = false;

        // Initialize
        this.init();
    }

    /**
     * Initialize news controller
     */
    async init() {
        console.log('📰 Initializing News Controller...');

        // Load initial news
        await this.loadNews();

        console.log('✅ News controller initialized');
    }

    /**
     * Load security news using shared news service
     */
    async loadNews() {
        if (!window.newsService) {
            console.error('News service not available');
            this.renderNewsErrorMessage();
            return;
        }

        console.log('📰 Loading security news using news service:', {
            limit: this.newsLimit,
            userId: this.userId
        });

        try {
            // Use news service to load and display news
            await window.newsService.loadAndDisplayNews('newsContainer', {
                limit: this.newsLimit,
                showLatest: true,
                detailed: false
            });
            console.log('✅ Security news loaded successfully');
        } catch (error) {
            console.error('🔴 Failed to load security news:', error);
            this.renderNewsErrorMessage();
        }
    }

    /**
     * Render news error message
     */
    renderNewsErrorMessage() {
        if (!this.ui.container) return;

        const errorHTML = `
            <div class="flex items-center justify-center h-full text-error">
                <div class="text-center p-4">
                    <span class="material-symbols-outlined text-3xl mb-2">error</span>
                    <p class="text-sm">Không thể tải tin tức bảo mật</p>
                </div>
            </div>
        `;
        // SECURE: Use safe innerHTML setter
        if (typeof CyberSecSanitizer !== 'undefined' && CyberSecSanitizer.safeSetInnerHTML) {
            CyberSecSanitizer.safeSetInnerHTML(this.ui.container, errorHTML);
        } else {
            this.ui.container.innerHTML = errorHTML; // Fallback
        }
    }

    /**
     * Refresh news
     */
    async refreshNews() {
        await this.loadNews();
    }

    /**
     * Set news limit
     * @param {number} limit - Maximum number of news items to display
     */
    setNewsLimit(limit) {
        if (typeof limit === 'number' && limit > 0) {
            this.newsLimit = limit;
        } else {
            console.warn('Invalid news limit:', limit);
        }
    }

    /**
     * Cleanup resources when controller is destroyed
     */
    cleanup() {
        if (this.isCleanedUp) {
            console.warn('⚠️ News controller already cleaned up, skipping');
            return;
        }

        console.log('🧹 Cleaning up news controller resources...');

        // Clear UI references
        if (this.ui && this.ui.container) {
            this.ui.container = null;
        }

        // Clear other references
        this.userId = null;
        this.apiEndpoint = null;

        // Mark as cleaned up
        this.isCleanedUp = true;

        console.log('✅ News controller cleaned up successfully');
    }
}