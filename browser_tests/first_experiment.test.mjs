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

const {
    focusFirstExperimentTarget,
    getFirstExperimentStep
} = await import(
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

test('the first experiment focuses the next useful closed-panel control', () => {
    const focused = [];
    const elements = {
        'trigger-chemicals': { focus: () => focused.push('trigger-chemicals') },
        'sub-panel-chemicals': { style: { display: 'none' } },
        'trigger-apparatus': { focus: () => focused.push('trigger-apparatus') },
        'sub-panel-apparatus': { style: { display: 'none' } },
        'btn-fire-analysis': { focus: () => focused.push('btn-fire-analysis') }
    };
    globalThis.document.getElementById = id => elements[id] || null;

    focusFirstExperimentTarget('chlorine');
    focusFirstExperimentTarget('beaker');
    focusFirstExperimentTarget('analyze');
    focusFirstExperimentTarget('complete');

    assert.deepEqual(focused, [
        'trigger-chemicals',
        'trigger-apparatus',
        'btn-fire-analysis'
    ]);
});
