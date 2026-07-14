const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots');
const adminUsername = process.env.E2E_ADMIN_USERNAME || 'admin';
const adminPassword = process.env.E2E_ADMIN_PASSWORD;
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function runAutomation() {
    if (!adminPassword) {
        throw new Error('E2E_ADMIN_PASSWORD must be set for browser automation');
    }
    console.log('=== STARTING BROWSER AUTOMATION ===');
    const browser = await chromium.launch({ headless: true });
    
    // Test list of viewports
    const devices = [
        { name: 'Desktop', width: 1280, height: 800, isMobile: false },
        { name: 'Tablet', width: 768, height: 1024, isMobile: true },
        { name: 'Mobile', width: 375, height: 667, isMobile: true }
    ];

    const logs = [];
    const errors = [];

    for (const dev of devices) {
        console.log(`\nTesting device: ${dev.name} (${dev.width}x${dev.height})`);
        
        const context = await browser.newContext({
            viewport: { width: dev.width, height: dev.height },
            isMobile: dev.isMobile
        });

        const page = await context.newPage();

        // Listen to console messages
        page.on('console', msg => {
            const text = msg.text();
            logs.push(`[Console] [${dev.name}] [${msg.type()}] ${text}`);
            if (msg.type() === 'error') {
                errors.push(`[Console Error] [${dev.name}] ${text}`);
            }
        });

        // Listen to page errors
        page.on('pageerror', err => {
            errors.push(`[Page Error] [${dev.name}] ${err.message}`);
        });

        // Listen to failed network requests
        page.on('requestfailed', req => {
            errors.push(`[Network Error] [${dev.name}] Failed to load ${req.url()}: ${req.failure().errorText}`);
        });

        try {
            // 1. Visit Login Page
            console.log('Visiting Login Page...');
            await page.goto('http://localhost:3000/login.html');
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_1_login.png`) });

            // 2. Perform validations
            console.log('Testing inputs and validation...');
            await page.fill('#input-username', 'a'); // too short
            await page.fill('#input-password', 'short'); // too short
            await page.click('#btn-submit');
            await page.waitForTimeout(500);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_2_validation_error.png`) });

            // 3. Log in as admin
            console.log('Logging in as Admin...');
            await page.fill('#input-username', adminUsername);
            await page.fill('#input-password', adminPassword);
            await page.click('#btn-submit');
            
            // Wait for redirection
            await page.waitForURL('**/pages/admin.html', { timeout: 15000 });
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_3_admin_panel.png`) });
            console.log('Admin login successful!');

            // 4. Click tabs on Admin Panel
            if (dev.name === 'Desktop') {
                console.log('Interacting with Admin Panel sections...');
                // Click Crawler configuration
                const crawlerTab = page.locator('a[href="#section-crawler"]');
                if (await crawlerTab.isVisible()) {
                    await crawlerTab.click();
                    await page.waitForTimeout(500);
                    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `admin_crawler_tab.png`) });
                }
                
                // Click RAG manager tab
                const ragTab = page.locator('a[href="#section-rag"]');
                if (await ragTab.isVisible()) {
                    await ragTab.click();
                    await page.waitForTimeout(500);
                    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `admin_rag_tab.png`) });
                }
            }

            // 5. Navigate to Dashboard
            console.log('Navigating to Dashboard...');
            await page.goto('http://localhost:3000/dashboard.html');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_4_dashboard.png`) });

            // 6. Navigate to URL Checker
            console.log('Navigating to URL Checker...');
            await page.goto('http://localhost:3000/pages/url-check/index.html');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_5_url_checker.png`) });

            // Test URL checker submit
            console.log('Submitting a URL to scanner...');
            const urlInput = page.locator('#urlInput');
            if (await urlInput.isVisible()) {
                await urlInput.fill('https://google.com');
                const checkBtn = page.locator('button:has-text("Kiểm tra")');
                if (await checkBtn.isVisible()) {
                    await checkBtn.click();
                    await page.waitForTimeout(1500);
                    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_6_url_check_result.png`) });
                }
            }

            // 7. Navigate to Security News
            console.log('Navigating to Security News...');
            await page.goto('http://localhost:3000/pages/news/index.html');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_7_news.png`) });

            // 8. Navigate to AI Assistant (Chat)
            console.log('Navigating to AI Assistant...');
            await page.goto('http://localhost:3000/pages/assistant/chat.html');
            await page.waitForTimeout(1000);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_8_chat.png`) });

            // Type a message
            const textarea = page.locator('textarea');
            if (await textarea.isVisible()) {
                await textarea.fill('Hello Sentinel! Run diagnostic check.');
                const sendBtn = page.locator('button:has-text("send")');
                // Or find send icon button
                const finalSendBtn = sendBtn.first() || page.locator('button').last();
                await finalSendBtn.click();
                await page.waitForTimeout(3000); // Wait for response
                await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_9_chat_response.png`) });
            }

        } catch (err) {
            console.error(`Error during automation for ${dev.name}:`, err);
            errors.push(`[Automation Error] [${dev.name}] ${err.message}`);
            await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${dev.name}_error.png`) });
        } finally {
            await context.close();
        }
    }

    await browser.close();

    console.log('\n=== BROWSER AUTOMATION COMPLETE ===');
    console.log(`Total console/page logs: ${logs.length}`);
    console.log(`Total errors captured: ${errors.length}`);
    
    // Write summary log
    const reportData = {
        timestamp: new Date().toISOString(),
        viewportsTested: devices.map(d => d.name),
        logs,
        errors
    };
    fs.writeFileSync(path.join(__dirname, 'browser_automation_log.json'), JSON.stringify(reportData, null, 2));
    console.log('Logs written to browser_automation_log.json');
}

runAutomation();
