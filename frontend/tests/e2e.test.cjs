const { test, expect } = require('@playwright/test');

// Keep track of a randomly generated user for login/signup tests
const testUsername = `user_${Date.now()}`;
const testEmail = `${testUsername}@example.com`;
const testPassword = 'Password123!'; // Strong password matching requirements
const testFullName = 'Test Agent';
const adminUsername = process.env.E2E_ADMIN_USERNAME || 'admin';
const adminPassword = process.env.E2E_ADMIN_PASSWORD;

function requireAdminCredentials() {
    if (!adminPassword) {
        test.skip(true, 'E2E_ADMIN_PASSWORD is required for admin E2E scenarios');
    }
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
        await page.click('#btn-submit');
        
        // Validation messages should appear in alert container
        const alert = page.locator('#alert-container');
        await expect(alert).toBeVisible();
        await expect(alert).not.toBeEmpty();

        // Fill invalid email and weak password
        await page.fill('#input-fullname', 'A'); // Too short fullname
        await page.fill('#input-email', 'invalid-email');
        await page.fill('#input-username', 'usr');
        await page.fill('#input-password', 'weak'); // Weak password (< 8 chars, no uppercase, etc.)
        
        await page.click('#btn-submit');
        await expect(alert).toBeVisible();
        await expect(alert).not.toBeEmpty();
    });

    test('3. Register a new user successfully', async ({ page }) => {
        await page.goto('/login.html');
        await page.click('#tab-register');

        await page.fill('#input-fullname', testFullName);
        await page.fill('#input-email', testEmail);
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);

        // Submit form
        await page.click('#btn-submit');

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
        
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);

        await page.click('#btn-submit');
        await page.waitForURL(/.*dashboard\.html/);
        await expect(page.locator('a[href="dashboard.html"]')).toBeVisible();
    });

    test('6. Non-admin user cannot access Admin Panel', async ({ page }) => {
        // Log in as user
        await page.goto('/login.html');
        await page.fill('#input-username', testUsername);
        await page.fill('#input-password', testPassword);
        await page.click('#btn-submit');
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
        await page.goto('/login.html');
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);

        await page.click('#btn-submit');
        
        // Should redirect to admin panel
        await page.waitForURL(/.*pages\/admin\.html/);
        await expect(page.locator('#admin-username')).toHaveText('admin');
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
