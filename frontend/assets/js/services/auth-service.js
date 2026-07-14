/**
 * CyberSec Assistant - Authentication Helper
 * Manages JWT tokens, session state, route protection, and global fetch interception.
 * Enhanced with AES-GCM encryption for JWT token storage.
 */
class AuthHelper {
    constructor() {
        this.apiEndpoint = window.location.origin;
        this.encryptionSecret = this.getOrCreateEncryptionSecret();
        this.init();
    }

    /**
     * Get or create encryption secret for token storage
     * @returns {string} Encryption secret
     */
    getOrCreateEncryptionSecret() {
        let secret = localStorage.getItem('cybersec_encryption_secret');
        if (secret) {
            return secret;
        }

        if (typeof CryptoUtils !== 'undefined' && CryptoUtils.generateSecret) {
            secret = CryptoUtils.generateSecret();
        } else {
            secret = Array.from({ length: 32 }, () =>
                Math.floor(Math.random() * 36).toString(36)
            ).join('');
        }

        localStorage.setItem('cybersec_encryption_secret', secret);
        return secret;
    }

    init() {
        // 1. Setup Fetch Interceptor to inject JWT Token and handle 401s
        this.setupFetchInterceptor();

        // 2. Run Route Guard to protect pages
        this.protectRoutes();

        // 3. Bind events and personalize UI on DOM load
        const initializeUI = () => {
            this.personalizeUI();
            this.initTopBar();
        };

        if (document.readyState !== 'loading') {
            initializeUI();
            return;
        }

        document.addEventListener('DOMContentLoaded', initializeUI);
    }

    /**
     * Intercept all window.fetch calls to automatically add authorization headers
     */
    setupFetchInterceptor() {
        const originalFetch = window.fetch;
        const self = this;

        window.fetch = async function (url, options = {}) {
            options.headers = options.headers || {};

            // Get token (async for encrypted token support)
            const token = await self.getToken();
            const userId = self.getUserId();

            // Inject JWT Token (primary authentication method)
            if (token) {
                options.headers['Authorization'] = `Bearer ${token}`;
            }
            // Inject fallback header ONLY when JWT is not present
            // This prevents X-User-ID spoofing when JWT is available
            else if (userId) {
                options.headers['X-User-ID'] = userId;
            }

            try {
                const response = await originalFetch(url, options);

                if (response.status !== 401) {
                    return response;
                }

                if (!url.includes('/api/auth/login') && !url.includes('/api/auth/register')) {
                    console.warn('Session expired or unauthorized. Logging out...');
                    localStorage.removeItem('cybersec_user_role');
                    self.logout();
                }
                return response;
            } catch (error) {
                console.error('Fetch error:', error);
                throw error;
            }
        };
    }

    /**
     * Verify the current session token against the backend.
     * Returns the user role if the token is valid, otherwise null.
     * This prevents stale/spoofed localStorage from granting access.
     * @returns {Promise<string|null>} User role or null
     */
    async verifySession() {
        const token = await this.getToken();
        if (!token) return null;

        try {
            const response = await fetch(`${this.apiEndpoint}/api/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) return null;
            const userData = await response.json();
            if (userData && userData.role) {
                // Refresh role from backend (authoritative source)
                localStorage.setItem('cybersec_user_role', userData.role);
                return userData.role;
            }
            return null;
        } catch (e) {
            console.warn('Session verification failed:', e);
            return null;
        }
    }

    /**
     * Protect dashboard and other pages from unauthorized access.
     * SECURITY: Always verifies the token against the backend before trusting
     * any role stored in localStorage. This prevents stale or spoofed sessions
     * from automatically granting access (e.g. to the admin panel).
     */
    async protectRoutes() {
        const token = await this.getToken();
        const path = window.location.pathname;
        const isLoginPage = path.endsWith('login.html') || path.endsWith('/login');

        if (!token) {
            if (!isLoginPage) {
                // Not logged in and accessing a protected page -> go to login
                console.log('🔒 Access denied. Redirecting to login...');
                window.location.href = this.getLoginRedirectUrl();
            }
            // On login page with no token: stay (do nothing)
            return;
        }

        // A token exists. Verify it with the backend before trusting any role.
        const verifiedRole = await this.verifySession();

        if (!verifiedRole) {
            // Token is invalid/expired or backend rejected it -> clear stale session.
            console.warn('🔒 Invalid or expired session. Clearing credentials...');
            // Clear without triggering a redirect loop: just remove storage items.
            localStorage.removeItem('cybersec_access_token_encrypted');
            localStorage.removeItem('cybersec_access_token');
            localStorage.removeItem('cybersec_username');
            localStorage.removeItem('cybersec_user_id');
            localStorage.removeItem('cybersec_user_role');
            if (!isLoginPage) {
                window.location.href = this.getLoginRedirectUrl();
            }
            // On login page: stay so the user can log in again.
            return;
        }

        // Token is valid.
        if (isLoginPage) {
            console.log('🔓 Already authenticated. Redirecting to dashboard...');
            window.location.href = this.getPostLoginRedirectUrl(verifiedRole);
        }
        // On a protected page with a valid token: allow access.
    }

    /**
     * Personalize user interface with logged-in credentials
     */
    personalizeUI() {
        const username = this.getUsername();
        if (!username) return;

        // Replace default Agent_701 with custom username
        document.querySelectorAll('*').forEach(el => {
            if (el.children.length === 0 && el.textContent.trim() === 'Agent_701') {
                el.textContent = username;
            }
        });

        // Check admin role and show admin link on sub-pages
        if (this.isAdmin()) {
            const adminLinks = document.querySelectorAll('#admin-link');
            adminLinks.forEach(link => {
                link.classList.remove('hidden');
                link.classList.add('flex');
                link.style.display = 'flex';
            });
        }

        // Inject logout button in the sidebar footer
        const sidebarFooters = document.querySelectorAll('nav div.border-t');
        sidebarFooters.forEach(footer => {
            // Check if logout button already exists
            if (footer.querySelector('.btn-logout')) return;

            const userContainer = footer.querySelector('div.flex');
            if (userContainer) {
                // Style parent container to contain elements side-by-side or block
                userContainer.classList.add('justify-between', 'w-full');
                
                // Create logout button
                const logoutBtn = document.createElement('button');
                logoutBtn.className = 'btn-logout text-on-surface-variant hover:text-error transition-colors ml-auto p-1 rounded-lg hover:bg-white/5 flex items-center justify-center';
                logoutBtn.title = 'Đăng xuất';
                logoutBtn.innerHTML = '<span class="material-symbols-outlined text-sm">logout</span>';
                
                logoutBtn.addEventListener('click', () => {
                    if (confirm('Bạn có chắc chắn muốn đăng xuất?')) {
                        this.logout();
                    }
                });

                userContainer.appendChild(logoutBtn);
            }
        });
    }

    /**
     * Log in user
     */
    async login(username, password) {
        try {
            const response = await fetch(`${this.apiEndpoint}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Đăng nhập thất bại.');
            }

            await this.setSession(data.access_token, data.username, data.user_id);

            // Fetch and store user role
            let role = null;
            try {
                const meResponse = await fetch(`${this.apiEndpoint}/api/auth/me`, {
                    headers: { 'Authorization': `Bearer ${data.access_token}` }
                });
                if (meResponse.ok) {
                    const userData = await meResponse.json();
                    role = userData.role;
                    localStorage.setItem('cybersec_user_role', role);
                    console.log(`✅ User role: ${userData.role}`);
                }
            } catch (e) {
                console.warn('Could not fetch user role:', e);
            }

            return { success: true, message: data.message, role };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Register new user
     */
    async register(username, email, fullName, password) {
        try {
            const response = await fetch(`${this.apiEndpoint}/api/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    email,
                    full_name: fullName || undefined,
                    password
                })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || 'Đăng ký thất bại.');
            }

            await this.setSession(data.access_token, data.username, data.user_id);
            return { success: true, message: data.message, role: null };
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Destroy session and redirect to login
     */
    logout() {
        // Remove encrypted token
        localStorage.removeItem('cybersec_access_token_encrypted');
        // Remove unencrypted token (if exists)
        localStorage.removeItem('cybersec_access_token');
        localStorage.removeItem('cybersec_username');
        localStorage.removeItem('cybersec_user_id');
        localStorage.removeItem('cybersec_user_role');
        window.location.href = this.getLoginRedirectUrl();
    }

    // Storage accessors
    /**
     * Get JWT token (decrypts if encrypted)
     * @returns {string|null} JWT token or null
     */
    async getToken() {
        // Try to get encrypted token first
        const encryptedToken = localStorage.getItem('cybersec_access_token_encrypted');
        if (encryptedToken && typeof CryptoUtils !== 'undefined') {
            try {
                const decrypted = await CryptoUtils.decrypt(encryptedToken, this.encryptionSecret);
                if (decrypted) return decrypted;
            } catch (error) {
                console.warn('Token decryption failed, trying fallback:', error);
            }
        }

        // Fallback to unencrypted token
        return localStorage.getItem('cybersec_access_token');
    }

    /**
     * Synchronous token getter (returns cached unencrypted token)
     * Use this when you need token synchronously
     * @returns {string|null} JWT token or null
     */
    getTokenSync() {
        return localStorage.getItem('cybersec_access_token');
    }

    getUsername() { return localStorage.getItem('cybersec_username'); }
    getUserId() { return localStorage.getItem('cybersec_user_id'); }
    getUserRole() { return localStorage.getItem('cybersec_user_role'); }
    isAdminRole(role) { return role === 'admin' || role === 'security_analyst'; }
    isAdmin() { return this.isAdminRole(this.getUserRole()); }

    /**
     * Set session with encrypted token storage
     * @param {string} token - JWT access token
     * @param {string} username - Username
     * @param {string} userId - User ID
     */
    async setSession(token, username, userId) {
        // Try to encrypt token for secure storage
        if (typeof CryptoUtils !== 'undefined' && CryptoUtils.encrypt) {
            try {
                const encrypted = await CryptoUtils.encrypt(token, this.encryptionSecret);
                if (encrypted) {
                    localStorage.setItem('cybersec_access_token_encrypted', encrypted);
                    localStorage.removeItem('cybersec_access_token'); // Remove unencrypted version
                    console.log('✅ Token encrypted and stored securely');
                } else {
                    // Encryption failed, store unencrypted
                    localStorage.setItem('cybersec_access_token', token);
                    console.warn('⚠️ Token encryption failed, using unencrypted storage');
                }
            } catch (error) {
                console.warn('Token encryption error, using unencrypted storage:', error);
                localStorage.setItem('cybersec_access_token', token);
            }
        } else {
            // CryptoUtils not available, store unencrypted
            localStorage.setItem('cybersec_access_token', token);
            console.warn('⚠️ CryptoUtils not available, using unencrypted storage');
        }

        localStorage.setItem('cybersec_username', username);
        localStorage.setItem('cybersec_user_id', userId);
    }

    // Path helpers
    getLoginRedirectUrl() {
        return '/login.html';
    }

    getDashboardRedirectUrl() {
        return '/dashboard.html';
    }

    getPostLoginRedirectUrl(role = this.getUserRole()) {
        return this.isAdminRole(role)
            ? '/pages/admin.html'
            : this.getDashboardRedirectUrl();
    }

    getChatRedirectUrl() {
        const path = window.location.pathname;
        if (!path.includes('/pages/')) {
            return 'pages/assistant/chat.html';
        }
        if (path.includes('/assistant/')) {
            return 'chat.html';
        }
        return '../assistant/chat.html';
    }

    initTopBar() {
        const searchInput = document.getElementById('topBarSearchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const query = searchInput.value.trim();
                    if (query) {
                        window.location.href = this.getChatRedirectUrl() + '?message=' + encodeURIComponent(query);
                    }
                }
            });
        }

        const notificationBtn = document.getElementById('topBarNotificationsBtn');
        const accountBtn = document.getElementById('topBarAccountBtn');

        if (notificationBtn || accountBtn) {
            const parent = (notificationBtn || accountBtn).parentElement;
            if (parent) {
                parent.classList.add('relative');
            }
        }

        if (notificationBtn) {
            notificationBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleNotificationsDropdown();
            });
        }

        if (accountBtn) {
            accountBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleAccountDropdown();
            });
        }

        document.addEventListener('click', () => {
            this.closeAllDropdowns();
        });
    }

    toggleNotificationsDropdown() {
        this.closeAllDropdowns('notifications');
        let dropdown = document.getElementById('topBarNotificationsDropdown');
        if (dropdown) {
            dropdown.remove();
            return;
        }

        const notificationBtn = document.getElementById('topBarNotificationsBtn');
        if (!notificationBtn) return;

        const parent = notificationBtn.parentElement;
        if (!parent) return;

        dropdown = document.createElement('div');
        dropdown.id = 'topBarNotificationsDropdown';
        dropdown.className = 'absolute right-8 top-12 w-80 bg-[#131316]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] rounded-2xl p-4 z-50 text-left animate-fade-in-down';
        
        // SAFE: Use DOM manipulation instead of innerHTML to prevent XSS
        const headerDiv = document.createElement('div');
        headerDiv.className = 'flex items-center justify-between pb-3 border-b border-white/[0.06] mb-3';

        const titleSpan = document.createElement('span');
        titleSpan.className = 'text-xs font-bold font-headline text-on-surface uppercase tracking-wider';
        titleSpan.textContent = 'Thông báo bảo mật';

        const badgeSpan = document.createElement('span');
        badgeSpan.className = 'text-[9px] font-mono text-outline font-bold bg-surface-container-high px-2 py-0.5 rounded';
        badgeSpan.textContent = '0 MỚI';

        headerDiv.appendChild(titleSpan);
        headerDiv.appendChild(badgeSpan);
        dropdown.appendChild(headerDiv);

        const notificationsDiv = document.createElement('div');
        notificationsDiv.className = 'space-y-3 max-h-60 overflow-y-auto pr-1';

        const emptyState = document.createElement('div');
        emptyState.className = 'text-center py-4 text-on-surface-variant text-xs';
        emptyState.innerHTML = '<span class="material-symbols-outlined text-base block mb-1">notifications_off</span>Chưa có thông báo mới';

        notificationsDiv.appendChild(emptyState);
        dropdown.appendChild(notificationsDiv);

        dropdown.addEventListener('click', (e) => e.stopPropagation());
        parent.appendChild(dropdown);
    }

    toggleAccountDropdown() {
        this.closeAllDropdowns('account');
        let dropdown = document.getElementById('topBarAccountDropdown');
        if (dropdown) {
            dropdown.remove();
            return;
        }

        const accountBtn = document.getElementById('topBarAccountBtn');
        if (!accountBtn) return;

        const parent = accountBtn.parentElement;
        if (!parent) return;

        const username = this.getUsername() || 'Agent_701';
        // SANITIZE: Prevent XSS by escaping username
        const sanitizedUsername = this.escapeHtml(username);

        dropdown = document.createElement('div');
        dropdown.id = 'topBarAccountDropdown';
        dropdown.className = 'absolute right-0 top-12 w-64 bg-[#131316]/95 backdrop-blur-xl border border-white/[0.08] shadow-[0_12px_40px_rgba(0,0,0,0.6)] rounded-2xl p-4 z-50 text-left animate-fade-in-down';

        // SAFE: Use DOM manipulation to prevent XSS
        const headerDiv = document.createElement('div');
        headerDiv.className = 'flex items-center gap-3 pb-3 border-b border-white/[0.06] mb-3';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'w-10 h-10 rounded-full bg-surface-container-highest flex items-center justify-center shrink-0 border border-white/[0.06] overflow-hidden';
        avatarDiv.innerHTML = '<img alt="User" src="/api/proxy/image?url=https://lh3.googleusercontent.com/aida-public/AB6AXuDBShGIiYfsmyeY7AbutPry9QdyNIb671EPriJpvgQO-qwpx4HnsvYrH_9d8wLb491z_ljwMhUXwafZkajhrZnr0CpG814lc-Wq677Q5qrvmrb3i5aoqaIVxYlRaD3QYUd0pWsYimH6VV5feypfDuOaFI_0lmAWDGK44QZOpjNBvLJIAgxV8MmCCcdcqgiKSoGRxF0WIxH2s1WcpV1xwMssXXVrjoRo-4LYcclHwQyM10l28R6P60WvI5V5A68BEXgj9Xb3-HxXeqw"/>';

        const userInfoDiv = document.createElement('div');
        userInfoDiv.className = 'flex-1 min-w-0';

        const usernameParagraph = document.createElement('p');
        usernameParagraph.className = 'text-sm font-bold font-headline text-on-surface truncate';
        usernameParagraph.textContent = sanitizedUsername; // SAFE: textContent prevents XSS

        const roleParagraph = document.createElement('p');
        roleParagraph.className = 'text-[10px] text-primary font-mono tracking-widest uppercase mt-0.5';
        roleParagraph.textContent = 'ANALYST_701';

        userInfoDiv.appendChild(usernameParagraph);
        userInfoDiv.appendChild(roleParagraph);
        headerDiv.appendChild(avatarDiv);
        headerDiv.appendChild(userInfoDiv);
        dropdown.appendChild(headerDiv);

        const securityInfoDiv = document.createElement('div');
        securityInfoDiv.className = 'space-y-2';

        const sessionInfoDiv = document.createElement('div');
        sessionInfoDiv.className = 'flex items-center justify-between text-[10px] text-on-surface-variant font-headline uppercase pb-1';

        const sessionLabelSpan = document.createElement('span');
        sessionLabelSpan.textContent = 'Phiên an toàn';

        const sessionValueSpan = document.createElement('span');
        sessionValueSpan.className = 'text-primary font-mono font-bold';
        sessionValueSpan.textContent = '128-bit SSL';

        sessionInfoDiv.appendChild(sessionLabelSpan);
        sessionInfoDiv.appendChild(sessionValueSpan);
        securityInfoDiv.appendChild(sessionInfoDiv);

        const dividerDiv = document.createElement('div');
        dividerDiv.className = 'h-px bg-white/[0.06] my-2';
        securityInfoDiv.appendChild(dividerDiv);

        const logoutButton = document.createElement('button');
        logoutButton.id = 'topBarLogoutBtn';
        logoutButton.className = 'w-full flex items-center gap-3 px-3 py-2 rounded-xl text-on-surface-variant hover:text-error hover:bg-error/5 transition-all text-xs font-headline font-semibold';
        logoutButton.innerHTML = '<span class="material-symbols-outlined text-sm">logout</span><span>Đăng xuất</span>';

        securityInfoDiv.appendChild(logoutButton);
        dropdown.appendChild(securityInfoDiv);

        dropdown.addEventListener('click', (e) => e.stopPropagation());
        parent.appendChild(dropdown);

        const logoutBtn = document.getElementById('topBarLogoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => {
                if (confirm('Bạn có chắc chắn muốn đăng xuất khỏi hệ thống?')) {
                    this.logout();
                }
            });
        }
    }

    closeAllDropdowns(except) {
        if (except !== 'notifications') {
            const d = document.getElementById('topBarNotificationsDropdown');
            if (d) d.remove();
        }
        if (except !== 'account') {
            const d = document.getElementById('topBarAccountDropdown');
            if (d) d.remove();
        }
    }

    /**
     * Escape HTML to prevent XSS attacks
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        if (!text || typeof text !== 'string') return '';

        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Expose singleton instance globally
window.auth = new AuthHelper();
