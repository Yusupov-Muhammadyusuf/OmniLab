import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = {
    getElementById: () => null
};
globalThis.window = {
    reactionDemo: null
};

const { parseSavedChemicals } = await import(
    '../static/js/configuration/config.js'
);

test('missing saved chemicals have no restored state', () => {
    assert.equal(parseSavedChemicals(null), null);
});

test('malformed saved chemical JSON is rejected', () => {
    assert.equal(parseSavedChemicals('not-json'), null);
});

test('non-array saved chemical values are rejected', () => {
    for (const value of [null, { chemical: 'Na' }, 'Na', 2, true]) {
        assert.equal(parseSavedChemicals(JSON.stringify(value)), null);
    }
});

test('unsupported and non-string chemical values are rejected', () => {
    for (const value of [
        ['Na', 'Xe'],
        ['Na', 'cl2'],
        ['Na', null],
        ['Na', 2]
    ]) {
        assert.equal(parseSavedChemicals(JSON.stringify(value)), null);
    }
});

test('duplicate saved chemical values are rejected', () => {
    for (const value of [['Na', 'Na'], ['Cl2', 'Cl2']]) {
        assert.equal(parseSavedChemicals(JSON.stringify(value)), null);
    }
});

test('supported unique saved chemical arrays are preserved', () => {
    for (const value of [[], ['Na'], ['Cl2'], ['Na', 'Cl2'], ['Cl2', 'Na']]) {
        assert.deepEqual(parseSavedChemicals(JSON.stringify(value)), value);
    }
});
