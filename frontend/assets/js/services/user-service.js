/**
 * User Service
 * Handles all user-related API communication
 */

class UserService {
    constructor() {
        this.apiEndpoint = window.config.get('apiEndpoint');
    }

    /**
     * Get current user profile
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} User profile
     */
    async getCurrentUser(token) {
        const requestUrl = `${this.apiEndpoint}/api/auth/me`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Unauthorized - token may be expired');
                }
                throw new Error(`User API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved user profile');
            return data;

        } catch (error) {
            console.error('🔴 User API error:', error);
            throw error;
        }
    }

    /**
     * Create user profile
     * @param {Object} userData - User data
     * @returns {Promise<Object>} Created user
     */
    async createUser(userData) {
        const requestUrl = `${this.apiEndpoint}/api/profiles/`;

        try {
            const response = await fetch(requestUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                throw new Error(`Create user API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ User profile created successfully');
            return data;

        } catch (error) {
            console.error('🔴 Create user error:', error);
            throw error;
        }
    }

    /**
     * Update user profile
     * @param {string} userId - User ID
     * @param {Object} userData - Updated user data
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} Updated user
     */
    async updateUser(userId, userData, token) {
        const requestUrl = `${this.apiEndpoint}/api/profiles/${userId}`;

        try {
            const response = await fetch(requestUrl, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(userData)
            });

            if (!response.ok) {
                throw new Error(`Update user API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ User profile updated successfully');
            return data;

        } catch (error) {
            console.error('🔴 Update user error:', error);
            throw error;
        }
    }

    /**
     * Get user activity (admin only)
     * @param {string} userId - User ID
     * @param {string} token - Authentication token
     * @returns {Promise<Object>} User activity
     */
    async getUserActivity(userId, token) {
        const requestUrl = `${this.apiEndpoint}/api/admin/users/${userId}/activity`;

        try {
            const response = await fetch(requestUrl, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                throw new Error(`User activity API failed: ${response.status} ${response.statusText}`);
            }

            const data = await response.json();
            console.log('✅ Retrieved user activity');
            return data;

        } catch (error) {
            console.error('🔴 User activity API error:', error);
            throw error;
        }
    }

    /**
     * Check if user has admin role
     * @param {string} token - Authentication token
     * @returns {Promise<boolean>} Admin status
     */
    async checkAdminRole(token) {
        try {
            const user = await this.getCurrentUser(token);
            const isAdmin = user.role === 'admin' || user.role === 'security_analyst';

            if (isAdmin) {
                console.log(`✅ Admin access granted for user: ${user.username} (${user.role})`);
                // Store role in localStorage
                localStorage.setItem('cybersec_user_role', user.role || 'user');
            }

            return isAdmin;

        } catch (error) {
            console.error('🔴 Admin role check error:', error);
            return false;
        }
    }

    /**
     * Handle authentication error (token expired)
     * @param {Object} error - Error object
     */
    handleAuthError(error) {
        if (error.message.includes('Unauthorized') || error.message.includes('401')) {
            console.warn('Token expired, redirecting to login...');
            localStorage.clear();
            window.location.href = 'login.html';
        }
    }
}

// Export singleton instance
window.userService = new UserService();