const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadValidationUtils() {
    const context = vm.createContext({ window: {}, URL });
    const source = fs.readFileSync(
        path.join(__dirname, '..', 'assets', 'js', 'utils', 'validation-utils.js'),
        'utf8'
    );

    vm.runInContext(source, context, { filename: 'validation-utils.js' });
    return context.window.ValidationUtils;
}

function plainObject(value) {
    return JSON.parse(JSON.stringify(value));
}

test('password validation retains strength levels and ordered feedback', () => {
    const ValidationUtils = loadValidationUtils();

    assert.deepEqual(
        plainObject(ValidationUtils.validatePassword('')),
        { isValid: false, strength: 'weak', score: 0, issues: ['Password is required'] }
    );

    const medium = plainObject(ValidationUtils.validatePassword('abcdefgh'));
    assert.equal(medium.isValid, true);
    assert.equal(medium.strength, 'medium');
    assert.equal(medium.score, 2);
    assert.deepEqual(medium.issues, [
        'Password must contain at least one uppercase letter',
        'Password must contain at least one number',
        'Password must contain at least one special character'
    ]);

    const strong = plainObject(ValidationUtils.validatePassword('Abcdef12!'));
    assert.deepEqual(strong, { isValid: true, strength: 'strong', score: 5, issues: [] });
});
