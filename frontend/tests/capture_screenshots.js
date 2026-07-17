const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ASSETS_DIR = path.join(__dirname, '..', '..', 'docs', 'assets');
const adminUsername = 'admin';
const adminPassword = process.env.E2E_ADMIN_PASSWORD;
if (!adminPassword) {
    throw new Error('E2E_ADMIN_PASSWORD is required; provide an isolated QA credential in the environment.');
}

if (!fs.existsSync(ASSETS_DIR)) {
    fs.mkdirSync(ASSETS_DIR, { recursive: true });
}

async function captureScreenshots() {
    console.log('=== STARTING CAPTURE SCREENSHOTS AUTOMATION ===');
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1440, height: 900 },
        deviceScaleFactor: 1.5 // Ensure crisp screenshot quality
    });

    const page = await context.newPage();

    try {
        // --- 1. CHATBOT INTERFACE (SECURITY CHAT) ---
        console.log('1. Navigating to Login Page for Chatbot screenshot...');
        await page.goto('http://127.0.0.1:3000/login.html', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForSelector('#input-username', { timeout: 5000 });
        await page.waitForTimeout(3000); // Give styling time to render
        
        console.log('Logging in as admin...');
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);
        await page.click('#btn-submit');
        
        console.log('Waiting for authentication redirection...');
        await page.waitForTimeout(4000); // Wait for JWT setup and redirection
        
        console.log('Navigating to Assistant Chat page...');
        await page.goto('http://127.0.0.1:3000/pages/assistant/chat.html', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForSelector('#chatInput', { timeout: 10000 });
        await page.waitForTimeout(4000); // Wait for chat styles & history
        
        console.log('Sending security question...');
        const securityQuestion = 'Làm thế nào để phòng chống tấn công SQL Injection? Cho tôi các khuyến nghị bảo mật chính.';
        await page.fill('#chatInput', securityQuestion);
        await page.click('#sendButton');
        
        console.log('Waiting for response to stream...');
        await page.waitForTimeout(10000); // Wait for chatbot to finish streaming
        
        const chatScreenshotPath = path.join(ASSETS_DIR, '1_chatbot_interface.png');
        await page.screenshot({ path: chatScreenshotPath });
        console.log(`Saved: ${chatScreenshotPath}`);

        // --- 2. CVE ANALYSIS INTERFACE ---
        console.log('2. Querying CVE database via Chatbot...');
        await page.fill('#chatInput', 'Tra cứu thông tin chi tiết về lỗ hổng CVE-2021-44228 (Log4Shell)');
        await page.click('#sendButton');
        
        console.log('Waiting for CVE analysis response...');
        await page.waitForTimeout(10000); // Wait for CVE response
        
        const cveScreenshotPath = path.join(ASSETS_DIR, '2_cve_analysis.png');
        await page.screenshot({ path: cveScreenshotPath });
        console.log(`Saved: ${cveScreenshotPath}`);

        // --- 3. BACKEND API SWAGGER UI ---
        console.log('3. Navigating to Backend API Swagger UI...');
        await page.goto('http://127.0.0.1:8000/docs', { waitUntil: 'domcontentloaded', timeout: 15000 });
        await page.waitForSelector('.swagger-ui', { timeout: 10000 });
        await page.waitForTimeout(4000); // Let Swagger render everything nicely
        
        const swaggerScreenshotPath = path.join(ASSETS_DIR, '3_backend_swagger_ui.png');
        await page.screenshot({ path: swaggerScreenshotPath });
        console.log(`Saved: ${swaggerScreenshotPath}`);

        // --- 4. GRAFANA DASHBOARD ---
        console.log('4. Navigating to Grafana Dashboard...');
        try {
            await page.goto('http://127.0.0.1:3001/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
            await page.waitForSelector('input[name="user"]', { timeout: 10000 });
            await page.fill('input[name="user"]', 'admin');
            await page.fill('input[name="password"]', 'admin');
            await page.click('button[type="submit"]');
            
            console.log('Checking for Grafana password change prompt...');
            await page.waitForTimeout(3000);
            
            const skipButton = page.locator('button:has-text("Skip")');
            if (await skipButton.isVisible()) {
                console.log('Skipping Grafana password change prompt...');
                await skipButton.click();
                await page.waitForTimeout(3000);
            }
            
            console.log('Navigating to Grafana Home...');
            await page.goto('http://127.0.0.1:3001/?orgId=1', { waitUntil: 'domcontentloaded', timeout: 15000 });
            await page.waitForTimeout(6000); // Give time for charts to load
            
            const grafanaScreenshotPath = path.join(ASSETS_DIR, '4_grafana_dashboard.png');
            await page.screenshot({ path: grafanaScreenshotPath });
            console.log(`Saved: ${grafanaScreenshotPath}`);
        } catch (grafanaError) {
            console.error('Error capturing Grafana screenshot, capturing fallback:', grafanaError);
            const grafanaFallbackPath = path.join(ASSETS_DIR, '4_grafana_dashboard.png');
            await page.screenshot({ path: grafanaFallbackPath });
            console.log(`Saved Grafana Fallback: ${grafanaFallbackPath}`);
        }

        // --- 5. DOCKER CONTAINERS STATUS ---
        console.log('5. Rendering Docker containers status terminal...');
        let dockerPsOutput = '';
        try {
            dockerPsOutput = execSync('docker ps', { encoding: 'utf8' });
        } catch (err) {
            console.error('Error running docker ps:', err);
            dockerPsOutput = 'Error running docker ps: ' + err.message;
        }

        const terminalHtml = `
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="UTF-8">
        <title>Docker Status</title>
        <style>
          body {
            background-color: #0c0d10;
            color: #c9d1d9;
            font-family: 'Consolas', 'Courier New', Courier, monospace;
            padding: 40px;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            box-sizing: border-box;
          }
          .terminal-window {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            box-shadow: 0 12px 36px rgba(0,0,0,0.6);
            overflow: hidden;
            width: 100%;
            max-width: 1300px;
          }
          .terminal-header {
            background-color: #21262d;
            padding: 12px 18px;
            display: flex;
            align-items: center;
            border-bottom: 1px solid #30363d;
          }
          .dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
          }
          .dot.red { background-color: #f25f58; }
          .dot.yellow { background-color: #fbbe3c; }
          .dot.green { background-color: #3fc950; }
          .terminal-title {
            color: #8b949e;
            font-size: 13px;
            margin-left: auto;
            margin-right: auto;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
          }
          .terminal-body {
            padding: 24px;
            font-size: 13px;
            line-height: 1.6;
            overflow-x: auto;
          }
          .prompt {
            color: #58a6ff;
            margin-bottom: 12px;
          }
          .command {
            color: #f0883e;
          }
          pre {
            margin: 0;
            white-space: pre;
            color: #e6edf3;
            overflow-x: auto;
          }
        </style>
        </head>
        <body>
        <div class="terminal-window">
          <div class="terminal-header">
            <div class="dot red"></div>
            <div class="dot yellow"></div>
            <div class="dot green"></div>
            <div class="terminal-title">PowerShell - CyberSec Assistant Services</div>
          </div>
          <div class="terminal-body">
            <div class="prompt">PS D:\\Đồ án CNPM> <span class="command">docker ps</span></div>
            <pre>${dockerPsOutput}</pre>
          </div>
        </div>
        </body>
        </html>
        `;

        await page.setContent(terminalHtml);
        await page.waitForTimeout(1000);
        
        const dockerScreenshotPath = path.join(ASSETS_DIR, '5_docker_containers_status.png');
        await page.screenshot({ path: dockerScreenshotPath });
        console.log(`Saved: ${dockerScreenshotPath}`);

    } catch (err) {
        console.error('Automation encountered an error:', err);
    } finally {
        await browser.close();
        console.log('=== SCREENSHOT AUTOMATION COMPLETE ===');
    }
}

captureScreenshots();
