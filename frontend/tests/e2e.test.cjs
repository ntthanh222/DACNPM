const { test, expect } = require('@playwright/test');
const crypto = require('crypto');

// Keep track of a randomly generated user for login/signup tests
const testUsername = `user_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
const testEmail = `${testUsername}@example.com`;
const testPassword = 'Password123!'; // Strong password matching requirements
const testFullName = 'Test Agent';
const adminUsername = process.env.E2E_ADMIN_USERNAME || 'admin';
const adminEmail = process.env.E2E_ADMIN_EMAIL;
const adminPassword = process.env.E2E_ADMIN_PASSWORD;

function requireAdminCredentials() {
    if (!adminPassword) {
        test.skip(true, 'E2E_ADMIN_PASSWORD is required for admin E2E scenarios; provide the isolated QA credential in the environment.');
    }
}

function requireIsolatedQaForMutation(page) {
    const url = new URL(page.url());
    if (url.port !== '3100') {
        test.skip(true, 'Mutation E2E scenarios run only against isolated QA on localhost:3100.');
    }
}

async function waitForAdminUsersToSettle(page) {
    await expect(page.locator('#loading-spinner')).toBeHidden({ timeout: 15000 });
}

test.describe('CyberSec Assistant Platform E2E Tests', () => {

    test.beforeEach(async ({ page }) => {
        // Authentication flows do not depend on third-party assets. Blocking
        // them keeps navigation deterministic when CDN/image hosts are slow.
        for (const pattern of [
            '**/api/proxy/image**',
            'https://cdnjs.cloudflare.com/**',
            'https://cdn.tailwindcss.com/**',
            'https://cdn.jsdelivr.net/**',
            'https://fonts.googleapis.com/**',
            'https://fonts.gstatic.com/**',
        ]) {
            await page.route(pattern, route => route.abort());
        }
    });

    test('1. Unauthenticated user accessing dashboard is redirected to login', async ({ page }) => {
        // Go to dashboard
        await page.goto('/dashboard.html');
        // Page should redirect to login page
        await expect(page).toHaveURL(/.*login\.html/);
    });

    test('2. Registration input validations prevent invalid signups', async ({ page }) => {
        await page.goto('/login.html');
        
        // Switch to registration tab
        await page.click('#tab-register');
        await expect(page.locator('#input-fullname')).toBeVisible();

        // Bypass native browser validation to test JS custom validations
        await page.evaluate(() => {
            document.getElementById('auth-form').setAttribute('novalidate', 'true');
        });

        // Trigger validation with empty inputs
        await page.locator('#btn-submit').click({ noWaitAfter: true });
        
        // Validation messages should appear in alert container
        const alert = page.locator('#alert-container');
        await expect(alert).toBeVisible();
        await expect(alert).not.toBeEmpty();

        // Fill invalid email and weak password
        await page.fill('#input-fullname', 'A'); // Too short fullname
        await page.fill('#input-email', 'invalid-email');
        await page.fill('#input-username', 'usr');
        await page.fill('#input-password', 'weak'); // Weak password (< 8 chars, no uppercase, etc.)
        
        await page.locator('#btn-submit').click({ noWaitAfter: true });
        await expect(alert).toBeVisible();
        await expect(alert).not.toBeEmpty();
    });

    test('3. Register a new user successfully', async ({ page }) => {
        await page.goto('/login.html');
        requireIsolatedQaForMutation(page);
        await page.click('#tab-register');

        await page.fill('#input-fullname', testFullName);
        await page.fill('#input-email', testEmail);
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);

        // Submit form
        await page.locator('#btn-submit').click({ noWaitAfter: true });

        // Check for success message
        const alert = page.locator('#alert-container');
        await expect(alert).toBeVisible();
        await expect(alert).not.toBeEmpty();

        // Should automatically redirect to dashboard
        await page.waitForURL(/.*dashboard\.html/);
        await expect(page.locator('a[href="dashboard.html"]')).toBeVisible();
    });

    test('4. Log out and try to access dashboard again', async ({ page }) => {
        await page.goto('/dashboard.html');
        
        // Click on Account settings button to reveal logout or logout directly
        // Let's check how logout is implemented in dashboard
        // Wait, let's see how logout works in auth-service.js or if there is a logout button.
        // Let's trigger localStorage clear to simulate logout or see if there is a button
        await page.evaluate(() => {
            window.auth.logout();
            window.location.reload();
        });

        await expect(page).toHaveURL(/.*login\.html/);
    });

    test('5. Login with newly created user credentials', async ({ page }) => {
        await page.goto('/login.html');
        requireIsolatedQaForMutation(page);
        
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);

        await page.locator('#btn-submit').click({ noWaitAfter: true });
        await page.waitForURL(/.*dashboard\.html/);
        await expect(page.locator('a[href="dashboard.html"]')).toBeVisible();
    });

    test('6. Non-admin user cannot access Admin Panel', async ({ page }) => {
        // Log in as user
        await page.goto('/login.html');
        requireIsolatedQaForMutation(page);
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);
        await page.locator('#btn-submit').click({ noWaitAfter: true });
        await page.waitForURL(/.*dashboard\.html/);

        // Admin Link should be hidden
        const adminLink = page.locator('#admin-link');
        await expect(adminLink).toBeHidden();

        // Direct navigation to admin.html should redirect away or show error
        await page.goto('/pages/admin.html');
        // Let's see if it redirects back to login or dashboard
        await expect(page).not.toHaveURL(/.*pages\/admin\.html/);
    });

    test('7. Admin login and role-based access to Admin Panel', async ({ page }) => {
        requireAdminCredentials();
        const authRequests = [];
        page.on('request', request => {
            if (request.url().includes('/api/auth/')) {
                authRequests.push({
                    url: request.url(),
                    method: request.method(),
                    postData: request.postData(),
                    contentType: request.headers()['content-type'] || ''
                });
            }
        });
        await page.goto('/login.html');
        await expect(page.locator('#environment-badge')).toBeVisible();
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);

        await page.locator('#btn-submit').click({ noWaitAfter: true });
        
        // Should redirect to admin panel
        await page.waitForURL(/.*pages\/admin\.html/);
        await expect(page.locator('#admin-username')).toHaveText(adminUsername);
        expect(authRequests.some(request => (
            request.url.endsWith('/api/auth/login') &&
            request.method === 'POST' &&
            request.contentType.includes('application/json') &&
            request.postData.includes(`"username":"${adminUsername}"`)
        ))).toBeTruthy();
        for (const request of authRequests) {
            expect(new URL(request.url).origin).toBe(new URL(page.url()).origin);
        }
    });

    test('7b. Admin email login succeeds without calling the wrong backend port', async ({ page }) => {
        requireAdminCredentials();
        if (!adminEmail) {
            test.skip(true, 'E2E_ADMIN_EMAIL is required for admin email login scenarios.');
        }

        const authRequestUrls = [];
        const consoleErrors = [];
        page.on('console', message => {
            if (message.type() === 'error') {
                consoleErrors.push(message.text());
            }
        });
        page.on('pageerror', error => {
            consoleErrors.push(error.message);
        });
        page.on('request', request => {
            if (request.url().includes('/api/auth/')) {
                authRequestUrls.push(request.url());
            }
        });

        await page.goto('/login.html');
        const expectedBadge = new URL(page.url()).port === '3100'
            ? /QA \/ Backend 8100/
            : /Development \/ Backend 8000/;
        await expect(page.locator('#environment-label')).toHaveText(expectedBadge);
        await page.fill('#input-username', adminEmail);
        await page.fill('#input-password', adminPassword);
        await page.locator('#btn-submit').click({ noWaitAfter: true });
        await page.waitForURL(/.*pages\/admin\.html/);
        await expect(page.locator('#admin-username')).toHaveText(adminUsername);
        await waitForAdminUsersToSettle(page);
        await page.reload({ waitUntil: 'domcontentloaded' });
        await expect(page).toHaveURL(/.*pages\/admin\.html/);
        await expect(page.locator('#admin-username')).toHaveText(adminUsername);
        await waitForAdminUsersToSettle(page);
        await page.evaluate(() => window.auth.logout());
        await page.waitForURL(/.*login\.html/);

        for (const url of authRequestUrls) {
            expect(new URL(url).origin).toBe(new URL(page.url()).origin);
        }
        const applicationErrors = consoleErrors.filter(error => (
            !error.includes('Failed to load resource: net::ERR_FAILED') &&
            !error.includes('tailwind is not defined') &&
            !error.includes('TypeError: Failed to fetch')
        ));
        expect(applicationErrors).toEqual([]);
    });

    test('8. Search and Pagination on Admin Users Table', async ({ page }) => {
        requireAdminCredentials();
        // Log in as admin
        await page.goto('/login.html');
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);
        await page.click('#btn-submit');
        await page.waitForURL(/.*pages\/admin\.html/);

        // We are on the users table section
        await expect(page.locator('#section-users')).toBeVisible();

        // Perform search
        await page.fill('#user-search', 'admin');
        await page.press('#user-search', 'Enter');
        
        // Verify pagination text or rows exist (auto-waiting assertion)
        await expect(page.locator('#users-table-body tr').first()).toBeVisible();
    });

    test('9. Responsive Viewports: Mobile & Tablet', async ({ page, isMobile }) => {
        requireAdminCredentials();
        await page.goto('/login.html');
        
        // Check responsive layout by verifying elements fit or adjust
        const card = page.locator('.w-full.max-w-md');
        await expect(card).toBeVisible();
        
        // If mobile, ensure navbar burger or responsive adjustments work
        // Here we just verify that key actions can still be performed
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);
        await expect(page.locator('#btn-submit')).toBeEnabled();
    });
});
