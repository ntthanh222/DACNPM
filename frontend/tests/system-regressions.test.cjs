const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const frontendRoot = path.join(__dirname, '..');

function readFrontend(relativePath) {
    return fs.readFileSync(path.join(frontendRoot, relativePath), 'utf8');
}

test('URL check form disables credential autofill on target and password fields', () => {
    const source = readFrontend('pages/url-check/index.html');

    assert.match(source, /id="urlInput"[^>]*autocomplete="off"/);
    assert.match(source, /id="passwordInput"[^>]*autocomplete="new-password"/);
});

test('news page controller calls an existing news service method', () => {
    const controllerSource = readFrontend('assets/js/controllers/news-page-controller.js');
    const serviceSource = readFrontend('assets/js/services/news-service.js');

    const calledMethods = [
        ...controllerSource.matchAll(/window\.newsService\.([a-zA-Z0-9_]+)\(/g)
    ].map((match) => match[1]);

    for (const methodName of calledMethods) {
        assert.match(
            serviceSource,
            new RegExp(`(?:async\\s+)?${methodName}\\s*\\(`),
            `newsService.${methodName} must exist`
        );
    }
});

test('chat service streams through the chatbot endpoint', async () => {
    const configSource = readFrontend('assets/js/utils/config.js');
    const chatServiceSource = readFrontend('assets/js/services/chat-service.js');
    const requestedUrls = [];

    const context = {
        window: {
            location: {
                hostname: 'localhost',
                origin: 'http://localhost:3000'
            },
            fetch: async (url) => {
                requestedUrls.push(url);
                return {
                    ok: true,
                    body: {
                        getReader() {
                            return {
                                async read() {
                                    return { done: true };
                                }
                            };
                        }
                    }
                };
            }
        },
        fetch: async (...args) => context.window.fetch(...args),
        TextDecoder,
        console: { log() {}, warn() {}, error() {} }
    };

    vm.createContext(context);
    vm.runInContext(configSource, context);
    vm.runInContext(chatServiceSource, context);

    await context.window.chatService.streamMessage('hi', 'user-1');

    assert.equal(
        requestedUrls[0],
        'http://localhost:3000/api/chatbot/chat/stream?message=hi'
    );
});

test('frontend sources no longer reference the legacy streambot endpoint', () => {
    const files = [
        'assets/js/controllers/chat-page-controller.js',
        'assets/js/services/chat-service.js',
        'assets/js/utils/config.js',
        'pages/assistant/chat.html'
    ];

    for (const file of files) {
        assert.doesNotMatch(readFrontend(file), /streambot|\/api\/chat\/streambot/);
    }
});

test('admin page escapes data returned by users, news, crawler, and RAG APIs', () => {
    const source = readFrontend('pages/admin.html');

    assert.match(source, /function escapeHTML\(value\)/);
    assert.match(source, /escapeHTML\(user\.username\)/);
    assert.match(source, /escapeHTML\(article\.title\)/);
    assert.match(source, /escapeHTML\(run\.status\)/);
    assert.match(source, /escapeHTML\(doc\.content\)/);
});
