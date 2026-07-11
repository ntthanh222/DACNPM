const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadURLChecker(document) {
    const context = vm.createContext({
        document,
        window: {},
        console: { log() {}, warn() {}, error() {} },
        URLSearchParams,
        setTimeout() {}
    });
    const source = fs.readFileSync(
        path.join(__dirname, '..', 'assets', 'js', 'controllers', 'url-checker.js'),
        'utf8'
    );

    vm.runInContext(`${source}\nwindow.URLCheckerController = URLCheckerController;`, context, {
        filename: 'url-checker.js'
    });
    return context.window.URLCheckerController;
}

test('clearing URL results removes each matched result card once', () => {
    const removed = [];
    const document = {
        addEventListener() {},
        querySelectorAll(selector) {
            assert.equal(selector, '.col-span-12.bg-\\[\\#19191d\\].rounded-2xl.p-6.border-l-2');
            return [{ remove: () => removed.push('result') }, { remove: () => removed.push('error') }];
        }
    };
    const URLCheckerController = loadURLChecker(document);

    URLCheckerController.prototype.clearPreviousResults.call({});

    assert.deepEqual(removed, ['result', 'error']);
});
