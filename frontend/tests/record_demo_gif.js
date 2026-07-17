const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const { PNG } = require('pngjs');
const GIFEncoder = require('gif-encoder-2');

const adminUsername = 'admin';
const adminPassword = process.env.E2E_ADMIN_PASSWORD;
if (!adminPassword) {
    throw new Error('E2E_ADMIN_PASSWORD is required; provide an isolated QA credential in the environment.');
}
const OUTPUT_DIR = path.join(__dirname, '..', '..', 'docs', 'assets');
const GIF_PATH = path.join(OUTPUT_DIR, 'chatbot_demo.gif');

if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
}

async function recordGif() {
    console.log('=== STARTING CHATBOT DEMO GIF RECORDING ===');
    const width = 960;
    const height = 600;
    const fps = 3; // 3 frames per second (approx 333ms delay)
    const delay = Math.round(1000 / fps);

    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width, height },
        deviceScaleFactor: 1.0 // 1x resolution to keep GIF size small
    });

    const page = await context.newPage();
    const frames = [];
    let isCapturing = false;
    let captureInterval = null;

    // Helper to start screenshot capture loop
    function startCapturing() {
        if (isCapturing) return;
        isCapturing = true;
        console.log('📸 Started capturing frames...');
        captureInterval = setInterval(async () => {
            if (!isCapturing) return;
            try {
                const buffer = await page.screenshot({ type: 'png' });
                frames.push(buffer);
            } catch (err) {
                console.error('Error capturing frame:', err.message);
            }
        }, delay);
    }

    // Helper to stop screenshot capture loop
    function stopCapturing() {
        isCapturing = false;
        if (captureInterval) {
            clearInterval(captureInterval);
            console.log(`📸 Stopped capturing. Captured ${frames.length} frames.`);
        }
    }

    try {
        // 1. Visit Login Page (Wait until domcontentloaded to handle CDN slowness)
        console.log('Navigating to Login Page...');
        await page.goto('http://localhost:3000/login.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('#input-username');
        await page.waitForTimeout(1000);

        // Fill credentials
        console.log('Logging in as Admin...');
        await page.fill('#input-username', adminUsername);
        await page.fill('#input-password', adminPassword);
        await page.click('#btn-submit');

        // Wait for redirection to dashboard
        console.log('Waiting for redirection to dashboard...');
        await page.waitForURL('**/dashboard.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForTimeout(2000);

        // Go to chatbot page
        console.log('Navigating to Assistant Chat page...');
        await page.goto('http://localhost:3000/pages/assistant/chat.html', { waitUntil: 'domcontentloaded', timeout: 30000 });
        await page.waitForSelector('#chatInput');
        await page.waitForTimeout(3000); // Wait for chat initialization and settle

        // START RECORDING ONLY HERE (saves CPU and avoids timeouts)
        startCapturing();
        await page.waitForTimeout(1000); // Initial 1s pause in the GIF

        // Type security question character-by-character
        console.log('Typing security question...');
        const chatInput = page.locator('#chatInput');
        await chatInput.focus();
        await page.waitForTimeout(500);
        
        // Simulate real human typing speed
        await chatInput.pressSequentially('What is SQL injection?', { delay: 100 });
        await page.waitForTimeout(800);

        // Click send button
        console.log('Sending question...');
        await page.click('#sendButton');

        // Wait for response to start and finish
        console.log('Waiting for chatbot response to finish streaming...');
        await page.waitForTimeout(2000); // Wait for typing indicator to appear
        
        // Wait up to 25 seconds for typing indicator to disappear
        try {
            await page.waitForSelector('#typingIndicator', { state: 'detached', timeout: 25000 });
            console.log('Typing indicator is gone. Chatbot finished responding.');
        } catch (e) {
            console.warn('Timeout waiting for typing indicator to disappear, continuing...');
        }
        
        // Wait a few seconds at the end so the user can read the response in the GIF
        await page.waitForTimeout(4000);
        
        // Stop capturing
        stopCapturing();

        // 2. Encode frames into GIF
        if (frames.length === 0) {
            throw new Error('No frames captured!');
        }

        console.log(`Encoding ${frames.length} frames into GIF...`);
        const encoder = new GIFEncoder(width, height, 'neuquant', true);
        encoder.setDelay(delay);
        encoder.setRepeat(0); // Loop infinitely
        encoder.setQuality(10); // Image quality (10 is default, 1 is best)
        encoder.start();

        for (let i = 0; i < frames.length; i++) {
            if (i % 15 === 0) {
                console.log(`Processing frame ${i}/${frames.length}...`);
            }
            const png = PNG.sync.read(frames[i]);
            encoder.addFrame(png.data);
        }

        encoder.finish();
        const buffer = encoder.out.getData();
        fs.writeFileSync(GIF_PATH, buffer);
        console.log(`SUCCESS: Demo GIF successfully saved to ${GIF_PATH}`);

    } catch (err) {
        console.error('An error occurred during GIF recording automation:', err);
        stopCapturing();
    } finally {
        await browser.close();
        console.log('=== AUTOMATION FINISHED ===');
    }
}

recordGif();
