import assert from 'node:assert/strict';
import test from 'node:test';

globalThis.window = {
    firstExperiment: true,
    supportedReactionPairs: [['Na', 'Cl2']]
};
globalThis.document = {
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => []
};

const { getFirstExperimentStep } = await import(
    '../static/js/firstExperiment/firstExperiment.js'
);

test('the first experiment starts by asking for Sodium', () => {
    assert.equal(getFirstExperimentStep([], 'flask', false), 'sodium');
});

test('the first experiment asks for Chlorine after Sodium', () => {
    assert.equal(getFirstExperimentStep(['Na'], 'flask', false), 'chlorine');
});

test('the first experiment asks for a beaker after the pair is selected', () => {
    assert.equal(
        getFirstExperimentStep(['Na', 'Cl2'], 'flask', false),
        'beaker'
    );
});

test('the first experiment unlocks analysis after the beaker is selected', () => {
    assert.equal(
        getFirstExperimentStep(['Na', 'Cl2'], 'beaker', false),
        'analyze'
    );
});

test('the first experiment finishes only after a complete result is visible', () => {
    assert.equal(
        getFirstExperimentStep(['Na', 'Cl2'], 'beaker', true),
        'complete'
    );
});
