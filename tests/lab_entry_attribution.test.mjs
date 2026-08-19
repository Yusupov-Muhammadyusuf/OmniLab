import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.document = {
    getElementById: () => null
};
globalThis.window = {
    location: { search: '' },
    reactionDemo: null
};

const { getLabEntryAttribution } = await import(
    '../static/js/configuration/config.js'
);

const preparedDemo = {
    id: 'limewater-carbon-dioxide',
    version: '2026-07-24',
    selectedChemicals: ['Ca(OH)2', 'CO2'],
    vessel: 'beaker',
    liquidColor: '#dceff7'
};

function setEntry(reactionDemo, search) {
    globalThis.window.reactionDemo = reactionDemo;
    globalThis.window.location.search = search;
}

test('a fixed guide source stays attached to its prepared reaction', () => {
    setEntry(preparedDemo, '?source=guide_observation_a');

    assert.deepEqual(getLabEntryAttribution(), {
        entry_source: 'guide',
        visit_source: 'guide_observation_a',
        prepared_reaction_id: 'limewater-carbon-dioxide'
    });
});

test('a prepared demo without a source is classified without guessing', () => {
    setEntry(preparedDemo, '');

    assert.deepEqual(getLabEntryAttribution(), {
        entry_source: 'prepared_demo',
        prepared_reaction_id: 'limewater-carbon-dioxide'
    });
});

test('a direct lab visit has no prepared reaction identifier', () => {
    setEntry(null, '');

    assert.deepEqual(getLabEntryAttribution(), {
        entry_source: 'direct'
    });
});

test('an unrecognized source is classified as unknown and not retained', () => {
    setEntry(preparedDemo, '?source=student-email@example.com');

    assert.deepEqual(getLabEntryAttribution(), {
        entry_source: 'unknown',
        prepared_reaction_id: 'limewater-carbon-dioxide'
    });
});
