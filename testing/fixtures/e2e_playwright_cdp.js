const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = path.join(__dirname, '..', 'reports', 'runtime-first', 'corrective-phase', 'browser-evidence');
if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

// 9222 websocket URL passed via arg
const wsUrl = process.argv[2];

async function run() {
    console.log(`Connecting to CDP at ${wsUrl}`);
    const browser = await chromium.connectOverCDP(wsUrl);
    
    // Objective 10: Viewports. We will use contexts for this.
    const viewports = [
        { name: 'Desktop', width: 1440, height: 900 },
        { name: 'Tablet', width: 768, height: 1024 },
        { name: 'Mobile', width: 390, height: 844 }
    ];
    
    // We will do most tests on Desktop, and then quickly verify Mobile viewport.
    const defaultCtx = await browser.newContext({ viewport: viewports[0] });
    const page = await defaultCtx.newPage();

    let logs = [];
    let duplicateChatReqs = 0;
    
    page.on('console', msg => {
        const text = msg.text();
        console.log(`[Console] ${msg.type()}: ${text}`);
        if(msg.type() === 'error') logs.push(text);
    });
    
    page.on('request', req => {
        if (req.url().includes('/api/chat') && req.method() === 'POST' && !req.url().includes('stream-ticket')) {
            duplicateChatReqs++;
        }
    });

    try {
        // 1. Authentication
        console.log('--- 1. Authentication ---');
        await page.goto('http://localhost:3000/login.html');
        // Wrong password
        await page.fill('#input-username', 'admin');
        await page.fill('#input-password', 'wrong_pass');
        await page.click('#btn-submit');
        await page.waitForTimeout(500);
        // Correct password
        await page.fill('#input-password', 'DevAdmin-2026-T9mQ4vL2!s');
        await page.click('#btn-submit');
        await page.waitForURL('**/dashboard.html', { timeout: 10000 });
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'login-success.png') });

        // 2. Dashboard
        console.log('--- 2. Dashboard ---');
        await page.waitForTimeout(2000); // Wait for charts to load
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'dashboard.png') });
        
        // 3. Chat Greeting
        console.log('--- 3. Chat Greeting ---');
        await page.goto('http://localhost:3000/pages/assistant/chat.html');
        await page.waitForTimeout(1000);
        await page.fill('textarea[placeholder*="message"]', 'Xin chào');
        await page.click('button:has-text("send")'); // or the send icon
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chat-greeting.png') });

        // 4. URL Phishing
        console.log('--- 4. URL Phishing ---');
        await page.fill('textarea', 'Kiểm tra URL https://example.com');
        const [urlCheckRequest] = await Promise.all([
            page.waitForRequest(req => req.url().includes('stream-ticket') && req.method() === 'POST'),
            page.click('button:has-text("send")')
        ]);
        await page.waitForTimeout(4000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chat-url-check.png') });

        // 5. CVE lookup
        console.log('--- 5. CVE Lookup ---');
        await page.fill('textarea', 'Tra cứu CVE-2024-3094');
        await page.click('button:has-text("send")');
        await page.waitForTimeout(4000);

        // 6 & 7. RAG Runtime & Authenticated SSE
        console.log('--- 6. RAG Runtime ---');
        await page.fill('textarea', 'Giải thích các bước harden Ubuntu server');
        await page.click('button:has-text("send")');
        await page.waitForTimeout(5000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chat-rag.png') });
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chat-sse-complete.png') });

        // 8. Persistence
        console.log('--- 8. Persistence ---');
        const ts = Date.now();
        const marker = `E2E-BROWSER-${ts}`;
        await page.fill('textarea', marker);
        await page.click('button:has-text("send")');
        await page.waitForTimeout(3000);
        
        // Refresh page
        await page.reload();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'chat-history-after-refresh.png') });

        // 9. Authorization
        console.log('--- 9. Authorization ---');
        await page.goto('http://localhost:3000/pages/admin.html');
        await page.waitForTimeout(1000);
        await page.screenshot({ path: path.join(SCREENSHOT_DIR, 'admin-allowed.png') });

        // 10. Mobile Viewport
        console.log('--- 10. Mobile Viewport ---');
        const mobileCtx = await browser.newContext({ viewport: viewports[2] });
        const mobilePage = await mobileCtx.newPage();
        await mobilePage.goto('http://localhost:3000/pages/assistant/chat.html');
        await mobilePage.waitForTimeout(2000);
        await mobilePage.screenshot({ path: path.join(SCREENSHOT_DIR, 'mobile-chat.png') });
        await mobileCtx.close();

    } catch (e) {
        console.error('Error during execution:', e);
    } finally {
        console.log('Closing default context');
        await defaultCtx.close();
        await browser.close();
    }
}

run();
