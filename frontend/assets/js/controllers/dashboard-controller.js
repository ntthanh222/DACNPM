/**
 * Dashboard Main Controller
 * Main orchestrator for dashboard functionality
 * Coordinates between chat, news, and stats controllers
 */
class DashboardController {
    constructor() {
        // Configuration
        this.apiEndpoint = window.config.get('apiEndpoint');
        this.chatbotEndpoint = window.config.get('chatbotEndpoint');
        this.phishingCheckEndpoint = window.config.get('phishingCheckEndpoint');
        this.passwordStrengthEndpoint = window.config.get('passwordStrengthEndpoint');

        // User identification
        this.userId = this.getOrCreateUserId();

        // Interval IDs for cleanup
        this.newsInterval = null;
        this.statsInterval = null;

        // Cleanup state tracking
        this.isCleanedUp = false;

        // Initialize sub-controllers
        this.chatController = null;
        this.newsController = null;
        this.statsController = null;

        // Initialize
        this.init();
    }

    /**
     * Initialize dashboard components
     */
    async init() {
        console.log('🚀 Initializing Dashboard Controller...');

        // Set welcome time
        this.setWelcomeTime();

        // Check if user is admin and show admin link
        await this.checkAdminRole();

        // Initialize sub-controllers
        this.initializeSubControllers();

        // Initialize REST API connection
        this.initializeConnection();

        // Setup event listeners
        this.setupEventListeners();

        // Setup cleanup handlers for page unload
        this.setupCleanupOnUnload();

        // Start periodic updates
        this.startPeriodicUpdates();

        console.log('✅ Dashboard initialized successfully');
    }

    /**
     * Setup cleanup handlers for page unload and visibility change
     */
    setupCleanupOnUnload() {
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (!this.isCleanedUp) {
                this.cleanup();
            }
        });

        // Cleanup when page becomes hidden (user navigates away)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden && !this.isCleanedUp) {
                console.log('👁️ Page hidden, cleaning up resources...');
                this.cleanup();
            }
        });

        // Cleanup on page hide (back/forward navigation)
        window.addEventListener('pagehide', () => {
            if (!this.isCleanedUp) {
                this.cleanup();
            }
        });
    }

    /**
     * Initialize sub-controllers
     */
    initializeSubControllers() {
        // Initialize chat controller
        if (typeof ChatController !== 'undefined') {
            this.chatController = new ChatController(this.userId, this.chatbotEndpoint);
            console.log('✅ Chat controller initialized');
        }

        // Initialize news controller
        if (typeof NewsController !== 'undefined') {
            this.newsController = new NewsController(this.userId, this.apiEndpoint);
            console.log('✅ News controller initialized');
        }

        // Initialize stats controller
        if (typeof StatsController !== 'undefined') {
            this.statsController = new StatsController(this.userId, this.apiEndpoint);
            console.log('✅ Stats controller initialized');
        }
    }

    /**
     * Check if current user has admin role and show admin link
     */
    async checkAdminRole() {
        try {
            const adminLink = document.getElementById('admin-link');
            if (adminLink) {
                // The markup also contains the flex utility class; explicitly
                // control display so non-admin users never see the link.
                adminLink.style.display = 'none';
            }
            const token = localStorage.getItem('cybersec_access_token');
            if (!token) return;

            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const user = await response.json();
                localStorage.setItem('cybersec_user_role', user.role || 'user');
                if (user.role === 'admin' || user.role === 'security_analyst') {
                    if (adminLink) {
                        adminLink.classList.remove('hidden');
                        adminLink.classList.add('flex');
                        adminLink.style.display = 'flex';
                        console.log(`Admin access granted for user: ${user.username} (${user.role})`);
                    }
                }
            } else if (response.status === 401) {
                console.warn('Token expired, redirecting to login...');
                localStorage.clear();
                window.location.href = 'login.html';
            } else {
                console.warn(`checkAdminRole failed: ${response.status} ${response.statusText}`);
            }
        } catch (error) {
            console.error('checkAdminRole error:', error);
        }
    }

    /**
     * User Identification - Generate or retrieve UUID
     */
    getOrCreateUserId() {
        // Check localStorage first to avoid redundant API calls
        const storedUserId = localStorage.getItem('cybersec_user_id');
        if (storedUserId) {
            this.userId = storedUserId;
            return storedUserId;
        }

        // Only call API if not in storage
        const userId = window.getOrCreateUserId();
        if (userId && !this.userId) {
            this.userId = userId;
            this.trackNewUser(userId);
        }
        return userId;
    }

    /**
     * Track new user in backend
     */
    async trackNewUser(userId) {
        try {
            const endpoint = this.apiEndpoint || window.location.origin;
            await fetch(`${endpoint}/api/profiles/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: `User_${userId.substring(0, 8)}`,
                    full_name: 'Anonymous User'
                })
            });
        } catch (error) {
            console.log('User tracking failed:', error);
        }
    }

    /**
     * Set welcome message timestamp
     */
    setWelcomeTime() {
        const welcomeTimeEl = document.getElementById('welcomeTime');
        if (welcomeTimeEl) {
            const now = new Date();
            const timeStr = now.toISOString().split('T')[1].split('.')[0] + ' UTC';
            welcomeTimeEl.textContent = timeStr;
        }
    }

    /**
     * Initialize REST API connection status
     */
    initializeConnection() {
        const connectionStatus = document.getElementById('connectionStatus');
        const connectionDot = document.getElementById('connectionDot');
        const connectionText = document.getElementById('connectionText');

        // Test API connection
        this.testApiConnection().then(isConnected => {
            if (isConnected) {
                connectionDot.className = 'w-1.5 h-1.5 rounded-full bg-primary animate-pulse';
                connectionText.textContent = 'Online';
                connectionText.className = 'text-primary';
                console.log('API connection established');
            } else {
                connectionDot.className = 'w-1.5 h-1.5 rounded-full bg-error';
                connectionText.textContent = 'Connection Failed';
                connectionText.className = 'text-error';
            }
        }).catch(error => {
            console.error('API connection test failed:', error);
            connectionDot.className = 'w-1.5 h-1.5 rounded-full bg-error';
            connectionText.textContent = 'Error';
            connectionText.className = 'text-error';
        });
    }

    /**
     * Test API connection
     */
    async testApiConnection() {
        try {
            const response = await fetch(`${this.apiEndpoint}/health`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });
            return response.ok;
        } catch (error) {
            console.error('API connection test failed:', error);
            return false;
        }
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Quick URL Check Action
        const quickUrlInput = document.getElementById('quickUrlInput');
        const quickUrlBtn = document.getElementById('quickUrlBtn');
        if (quickUrlInput && quickUrlBtn) {
            const executeQuickUrlScan = () => {
                const url = quickUrlInput.value.trim();
                if (url) {
                    window.location.href = `pages/url-check/index.html?url=${encodeURIComponent(url)}`;
                }
            };
            quickUrlBtn.addEventListener('click', executeQuickUrlScan);
            quickUrlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    executeQuickUrlScan();
                }
            });
        }

        // Quick AI Prompt Action
        const quickAiInput = document.getElementById('quickAiInput');
        const quickAiBtn = document.getElementById('quickAiBtn');
        if (quickAiInput && quickAiBtn) {
            const executeQuickAiPrompt = () => {
                const msg = quickAiInput.value.trim();
                if (msg) {
                    window.location.href = `pages/assistant/chat.html?message=${encodeURIComponent(msg)}`;
                }
            };
            quickAiBtn.addEventListener('click', executeQuickAiPrompt);
            quickAiInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    executeQuickAiPrompt();
                }
            });
        }

        // Refresh stats button
        const refreshStatsBtn = document.getElementById('refreshStatsBtn');
        if (refreshStatsBtn && this.statsController) {
            refreshStatsBtn.addEventListener('click', () => {
                this.statsController.loadStats();
            });
        }

        // Export report button
        const exportReportBtn = document.getElementById('exportReportBtn');
        if (exportReportBtn) {
            exportReportBtn.addEventListener('click', () => {
                this.exportSecurityReport();
            });
        }
    }

    /**
     * Export security scan report to CSV
     */
    async exportSecurityReport() {
        const exportUrl = `${this.apiEndpoint}/api/reports/security-scans/export`;

        try {
            // Show loading state
            const btn = document.getElementById('exportReportBtn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="material-symbols-outlined animate-spin">sync</span> Đang xuất...';
            }

            // Call export API
            const response = await fetch(exportUrl);

            if (!response.ok) {
                throw new Error(`Export failed: ${response.status}`);
            }

            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `security_scans_report_${new Date().toISOString().slice(0,10)}.csv`;
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="(.+)"/);
                if (match) {
                    filename = match[1];
                }
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            console.log(`✅ Report exported: ${filename}`);

        } catch (error) {
            console.error('❌ Export report failed:', error);
            alert('Không thể xuất báo cáo. Vui lòng thử lại sau.');
        } finally {
            // Reset button
            const btn = document.getElementById('exportReportBtn');
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<span class="material-symbols-outlined">download</span> Xuất báo cáo';
            }
        }
    }

    /**
     * Start periodic updates
     */
    startPeriodicUpdates() {
        // Don't start if already cleaned up
        if (this.isCleanedUp) {
            console.warn('⚠️ Dashboard cleaned up, skipping periodic updates');
            return;
        }

        // Clear existing intervals first to prevent duplicates
        this.stopPeriodicUpdates();

        // Update news every 5 minutes (300000 ms)
        if (this.newsController) {
            this.newsInterval = setInterval(() => {
                if (!this.isCleanedUp) {
                    this.newsController.loadNews();
                }
            }, 300000);
        }

        // Update stats every 10 minutes (600000 ms)
        if (this.statsController) {
            this.statsInterval = setInterval(() => {
                if (!this.isCleanedUp) {
                    this.statsController.loadStats();
                }
            }, 600000);
        }

        console.log('🔄 Started periodic updates (news: 5min, stats: 10min)');
    }

    /**
     * Stop periodic updates
     */
    stopPeriodicUpdates() {
        if (this.newsInterval) {
            clearInterval(this.newsInterval);
            this.newsInterval = null;
        }
        if (this.statsInterval) {
            clearInterval(this.statsInterval);
            this.statsInterval = null;
        }
        console.log('🛑 Stopped periodic updates');
    }

    /**
     * Cleanup resources when page is unloaded
     */
    cleanup() {
        if (this.isCleanedUp) {
            console.warn('⚠️ Dashboard already cleaned up, skipping');
            return;
        }

        console.log('🧹 Cleaning up dashboard resources...');

        // Clear periodic update intervals
        this.stopPeriodicUpdates();

        // Cleanup sub-controllers
        if (this.chatController && typeof this.chatController.cleanup === 'function') {
            this.chatController.cleanup();
            this.chatController = null;
        }
        if (this.newsController && typeof this.newsController.cleanup === 'function') {
            this.newsController.cleanup();
            this.newsController = null;
        }
        if (this.statsController && typeof this.statsController.cleanup === 'function') {
            this.statsController.cleanup();
            this.statsController = null;
        }

        // Clear references
        this.userId = null;

        // Mark as cleaned up
        this.isCleanedUp = true;

        console.log('✅ Dashboard cleaned up successfully');
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Prevent double initialization
    if (window.dashboardControllerInitialized) {
        console.warn('⚠️ Dashboard controller already initialized, skipping duplicate initialization');
        return;
    }

    const dashboard = new DashboardController();
    window.dashboardControllerInitialized = true;

    // Cleanup resources when page is unloaded
    window.addEventListener('beforeunload', () => {
        dashboard.cleanup();
    });
});
