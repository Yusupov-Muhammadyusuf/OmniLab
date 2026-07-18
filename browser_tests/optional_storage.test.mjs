import test from 'node:test';
import assert from 'node:assert/strict';

const storedValues = new Map();
const workingStorage = {
    getItem(key) {
        return storedValues.has(key) ? storedValues.get(key) : null;
    },
    setItem(key, value) {
        storedValues.set(key, value);
    },
    removeItem(key) {
        storedValues.delete(key);
    }
};

globalThis.window = { localStorage: workingStorage };

const {
    readStorageValue,
    removeStorageValue,
    writeStorageValue
} = await import('../static/js/storage/storage.js');

test('storage helpers preserve normal browser persistence', () => {
    writeStorageValue('savedChemicals', '["Na","Cl2"]');
    assert.equal(readStorageValue('savedChemicals'), '["Na","Cl2"]');

    removeStorageValue('savedChemicals');
    assert.equal(readStorageValue('savedChemicals'), null);
});

test('blocked storage reads behave like missing saved state', () => {
    window.localStorage = {
        getItem() {
            throw new DOMException('Storage blocked', 'SecurityError');
        }
    };

    assert.equal(readStorageValue('savedChemicals'), null);
    assert.equal(readStorageValue('savedLiquidColor'), null);
    assert.equal(readStorageValue('savedReaction'), null);
});

test('blocked storage writes and removals do not interrupt the session', () => {
    window.localStorage = {
        setItem() {
            throw new DOMException('Storage blocked', 'SecurityError');
        },
        removeItem() {
            throw new DOMException('Storage blocked', 'SecurityError');
        }
    };

    assert.doesNotThrow(() => writeStorageValue('savedChemicals', '["Na"]'));
    assert.doesNotThrow(() => writeStorageValue('savedReaction', '{}'));
    assert.doesNotThrow(() => removeStorageValue('savedChemicals'));
    assert.doesNotThrow(() => removeStorageValue('savedReaction'));
});

test('accessing browser storage may fail before a method can run', () => {
    Object.defineProperty(window, 'localStorage', {
        configurable: true,
        get() {
            throw new DOMException('Storage unavailable', 'SecurityError');
        }
    });

    assert.equal(readStorageValue('savedChemicals'), null);
    assert.doesNotThrow(() => writeStorageValue('savedChemicals', '["Na"]'));
    assert.doesNotThrow(() => removeStorageValue('savedChemicals'));
});
