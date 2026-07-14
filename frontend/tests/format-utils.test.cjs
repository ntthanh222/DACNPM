const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadFormatUtils() {
    const context = vm.createContext({ window: {} });
    const source = fs.readFileSync(
        path.join(__dirname, '..', 'assets', 'js', 'utils', 'format-utils.js'),
        'utf8'
    );

    vm.runInContext(source, context, { filename: 'format-utils.js' });
    return context.window.FormatUtils;
}

test('FormatUtils.formatBytes - happy paths and boundaries', () => {
    const FormatUtils = loadFormatUtils();

    // Happy paths
    assert.equal(FormatUtils.formatBytes(0), '0 Bytes');
    assert.equal(FormatUtils.formatBytes(1024), '1 KB');
    assert.equal(FormatUtils.formatBytes(1234567), '1.18 MB');
    assert.equal(FormatUtils.formatBytes(1073741824), '1 GB');

    // Decimals boundary
    assert.equal(FormatUtils.formatBytes(1234567, 0), '1 MB');
    assert.equal(FormatUtils.formatBytes(1234567, -5), '1 MB'); // negative decimals fallback to 0
    assert.equal(FormatUtils.formatBytes(1234567, 4), '1.1774 MB');
});

test('FormatUtils.formatNumber - inserts commas correctly', () => {
    const FormatUtils = loadFormatUtils();

    assert.equal(FormatUtils.formatNumber(0), '0');
    assert.equal(FormatUtils.formatNumber(100), '100');
    assert.equal(FormatUtils.formatNumber(1000), '1,000');
    assert.equal(FormatUtils.formatNumber(1000000), '1,000,000');
    assert.equal(FormatUtils.formatNumber(-1234567), '-1,234,567');
});

test('FormatUtils.formatPercentage - happy path and zero division', () => {
    const FormatUtils = loadFormatUtils();

    assert.equal(FormatUtils.formatPercentage(5, 10), '50.0%');
    assert.equal(FormatUtils.formatPercentage(1, 3, 2), '33.33%');
    assert.equal(FormatUtils.formatPercentage(5, 0), '0%'); // Division by zero boundary
});

test('FormatUtils.cvssToSeverity - matches CVSS scores to standard severities', () => {
    const FormatUtils = loadFormatUtils();

    assert.equal(FormatUtils.cvssToSeverity(10.0), 'critical');
    assert.equal(FormatUtils.cvssToSeverity(9.0), 'critical');
    assert.equal(FormatUtils.cvssToSeverity(8.9), 'high');
    assert.equal(FormatUtils.cvssToSeverity(7.0), 'high');
    assert.equal(FormatUtils.cvssToSeverity(6.9), 'medium');
    assert.equal(FormatUtils.cvssToSeverity(4.0), 'medium');
    assert.equal(FormatUtils.cvssToSeverity(3.9), 'low');
    assert.equal(FormatUtils.cvssToSeverity(0.1), 'low');
    assert.equal(FormatUtils.cvssToSeverity(0.0), 'info');
    assert.equal(FormatUtils.cvssToSeverity(-1.0), 'info'); // Invalid negative CVSS score boundary
});

test('FormatUtils.getSeverityColor - matches severity to colors', () => {
    const FormatUtils = loadFormatUtils();

    assert.equal(FormatUtils.getSeverityColor('critical'), 'text-error');
    assert.equal(FormatUtils.getSeverityColor('CRITICAL'), 'text-error'); // case insensitivity
    assert.equal(FormatUtils.getSeverityColor('high'), 'text-warning');
    assert.equal(FormatUtils.getSeverityColor('medium'), 'text-info');
    assert.equal(FormatUtils.getSeverityColor('low'), 'text-success');
    assert.equal(FormatUtils.getSeverityColor('info'), 'text-outline');
    assert.equal(FormatUtils.getSeverityColor('invalid'), 'text-outline'); // Invalid severity fallback
});

test('FormatUtils.formatIntent and formatSource - string capitalization', () => {
    const FormatUtils = loadFormatUtils();

    assert.equal(FormatUtils.formatIntent('scan_network'), 'Scan Network');
    assert.equal(FormatUtils.formatIntent(''), 'Unknown'); // Empty input boundary
    assert.equal(FormatUtils.formatIntent(null), 'Unknown'); // Null input boundary

    assert.equal(FormatUtils.formatSource('exploit_db'), 'Exploit Db');
    assert.equal(FormatUtils.formatSource(''), 'Unknown');
    assert.equal(FormatUtils.formatSource(null), 'Unknown');
});

test('FormatUtils.safeParse and safeStringify - json handling', () => {
    const FormatUtils = loadFormatUtils();

    // safeStringify
    assert.equal(FormatUtils.safeStringify({ a: 1 }), '{"a":1}');
    const circular = {};
    circular.self = circular;
    assert.equal(FormatUtils.safeStringify(circular), '{}'); // circular reference boundary

    // safeParse
    assert.deepEqual(JSON.parse(JSON.stringify(FormatUtils.safeParse('{"a":1}'))), { a: 1 });
    assert.equal(FormatUtils.safeParse('{invalid json}'), null); // invalid json boundary
});
