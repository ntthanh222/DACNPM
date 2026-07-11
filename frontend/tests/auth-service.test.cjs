const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const authServiceSource = fs.readFileSync(
    path.join(__dirname, '../assets/js/services/auth-service.js'),
    'utf8'
);
const loginPageSource = fs.readFileSync(
    path.join(__dirname, '../login.html'),
    'utf8'
);
const adminPageSource = fs.readFileSync(
    path.join(__dirname, '../pages/admin.html'),
    'utf8'
);

function response(body, ok = true) {
    return {
        ok,
        status: ok ? 200 : 401,
        async json() {
            return body;
        }
    };
}

function createAuthRuntime({ pathname = '/login.html', storedValues = {}, fetchImpl, cryptoUtils } = {}) {
    const values = new Map(Object.entries(storedValues));
    const localStorage = {
        getItem(key) {
            return values.has(key) ? values.get(key) : null;
        },
        setItem(key, value) {
            values.set(key, String(value));
        },
        removeItem(key) {
            values.delete(key);
        }
    };
    const location = { origin: 'http://localhost:3000', pathname, href: '' };
    const window = {
        location,
        localStorage,
        fetch: fetchImpl || (async () => response({}))
    };
    const context = {
        window,
        localStorage,
        fetch: window.fetch,
        document: {
            readyState: 'complete',
            addEventListener() {},
            getElementById() { return null; },
            querySelectorAll() { return []; }
        },
        console: { log() {}, warn() {}, error() {} },
        CryptoUtils: cryptoUtils,
        Array,
        Math
    };

    vm.createContext(context);
    vm.runInContext(authServiceSource, context);
    return { auth: window.auth, location, values };
}

test('routes admin and security analyst users to the admin panel', () => {
    const { auth } = createAuthRuntime();

    assert.equal(auth.getPostLoginRedirectUrl('admin'), '/pages/admin.html');
    assert.equal(auth.getPostLoginRedirectUrl('security_analyst'), '/pages/admin.html');
    assert.equal(auth.getPostLoginRedirectUrl('user'), '/dashboard.html');
});

test('login stores the role before returning the successful result', async () => {
    const requests = [];
    const cryptoUtils = {
        async encrypt() { return 'encrypted-token'; },
        async decrypt() { return 'access-token'; }
    };
    const { auth, values } = createAuthRuntime({
        cryptoUtils,
        fetchImpl: async (url, options) => {
            requests.push({ url, options });
            if (url.endsWith('/api/auth/login')) {
                return response({
                    access_token: 'access-token',
                    username: 'admin',
                    user_id: 'user-1',
                    message: 'Login successful'
                });
            }
            if (url.endsWith('/api/auth/me')) {
                return response({ role: 'admin' });
            }
            throw new Error(`Unexpected request: ${url}`);
        }
    });

    const result = await auth.login('admin', 'password');

    assert.equal(result.success, true, result.error);
    assert.equal(result.role, 'admin');
    assert.equal(values.get('cybersec_user_role'), 'admin');
    assert.equal(values.get('cybersec_access_token_encrypted'), 'encrypted-token');
    assert.equal(values.has('cybersec_access_token'), false);
    assert.equal(requests.length, 2);
});

test('route guard redirects to admin panel only after backend verifies an encrypted session', async () => {
    const cryptoUtils = {
        async encrypt() { return 'encrypted-token'; },
        async decrypt() { return 'access-token'; }
    };
    const { auth, location } = createAuthRuntime({
        storedValues: {
            cybersec_access_token_encrypted: 'encrypted-token',
            cybersec_user_role: 'admin'
        },
        cryptoUtils,
        fetchImpl: async (url) => {
            // SECURITY: route guard must verify the token against the backend
            // before trusting the role stored in localStorage.
            if (url.endsWith('/api/auth/me')) {
                return response({ role: 'admin' });
            }
            throw new Error(`Unexpected request: ${url}`);
        }
    });

    await auth.protectRoutes();

    assert.equal(location.href, '/pages/admin.html');
});

test('route guard clears stale session and stays on login when backend rejects the token', async () => {
    const cryptoUtils = {
        async encrypt() { return 'encrypted-token'; },
        async decrypt() { return 'access-token'; }
    };
    const { auth, location, values } = createAuthRuntime({
        storedValues: {
            cybersec_access_token_encrypted: 'encrypted-token',
            cybersec_user_role: 'admin'
        },
        cryptoUtils,
        fetchImpl: async (url) => {
            // Backend rejects the stale/spoofed token
            if (url.endsWith('/api/auth/me')) {
                return response({ detail: 'invalid' }, false);
            }
            throw new Error(`Unexpected request: ${url}`);
        }
    });

    await auth.protectRoutes();

    // Must NOT redirect into the admin panel based on localStorage alone
    assert.equal(location.href, '');
    // Stale credentials must be cleared
    assert.equal(values.has('cybersec_access_token_encrypted'), false);
    assert.equal(values.has('cybersec_user_role'), false);
});

test('login page loads crypto utilities exactly once before auth service', () => {
    const cryptoScriptMatches = loginPageSource.match(
        /<script[^>]+src="assets\/js\/utils\/crypto-utils\.js[^"\n]*"[^>]*><\/script>/g
    ) || [];
    const authScriptIndex = loginPageSource.indexOf('assets/js/services/auth-service.js');
    const cryptoScriptIndex = loginPageSource.indexOf('assets/js/utils/crypto-utils.js');

    assert.equal(cryptoScriptMatches.length, 1);
    assert.ok(cryptoScriptIndex >= 0);
    assert.ok(authScriptIndex > cryptoScriptIndex);
});

test('login form accepts an email identifier but registration keeps username validation', () => {
    assert.match(loginPageSource, /function isValidLoginIdentifier\(identifier\)/);
    assert.match(loginPageSource, /\\u00C0-\\u017F\\u1EA0-\\u1EF9\.@\+\-/);
    assert.match(loginPageSource, /currentTab === 'login'[\s\S]*isValidLoginIdentifier\(username\)/);
    assert.match(loginPageSource, /currentTab === 'register'[\s\S]*\^\[a-zA-Z0-9_\]\+\$/);
    assert.match(loginPageSource, /id="username-label"/);
});

test('admin page uses the shared encrypted session guard', () => {
    const cryptoScriptIndex = adminPageSource.indexOf(
        '../../assets/js/utils/crypto-utils.js'
    );
    const authScriptIndex = adminPageSource.indexOf(
        '../../assets/js/services/auth-service.js'
    );

    assert.ok(cryptoScriptIndex >= 0);
    assert.ok(authScriptIndex > cryptoScriptIndex);
    assert.match(adminPageSource, /authToken\s*=\s*await window\.auth\.getToken\(\)/);
    assert.doesNotMatch(
        adminPageSource,
        /let authToken\s*=\s*localStorage\.getItem\(['"]cybersec_access_token['"]\)/
    );
});

test('all protected pages load crypto utilities before auth service', () => {
    const protectedPagePaths = [
        '../pages/admin.html',
        '../pages/assistant/chat.html',
        '../pages/news/index.html',
        '../pages/news/detail.html',
        '../pages/url-check/index.html'
    ];

    for (const relativePath of protectedPagePaths) {
        const source = fs.readFileSync(path.join(__dirname, relativePath), 'utf8');
        const cryptoIndex = source.indexOf('assets/js/utils/crypto-utils.js');
        const authIndex = source.indexOf('assets/js/services/auth-service.js');

        assert.ok(cryptoIndex >= 0, `${relativePath} must load crypto utilities`);
        assert.ok(authIndex > cryptoIndex, `${relativePath} must load crypto before auth`);
    }
});
