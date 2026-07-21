import test from 'node:test';
import assert from 'node:assert/strict';

const { parseSavedReactionResult } = await import(
    '../static/js/interactions/reactionResult.js'
);

const completeResult = {
    equation: '2Na(s) + Cl2(g) -> 2NaCl(s)',
    explanation: 'The selected reactants form sodium chloride.',
    safety: 'Wear eye protection. | Keep sodium dry. | Use trained supervision.',
    effect: 'bubble'
};

test('missing and malformed saved reaction results are rejected', () => {
    assert.equal(parseSavedReactionResult(null), null);
    assert.equal(parseSavedReactionResult('not-json'), null);
});

test('non-object and wrongly typed saved reaction results are rejected', () => {
    for (const value of [
        null,
        [],
        'reaction',
        2,
        true,
        { ...completeResult, equation: 2 },
        { ...completeResult, explanation: null },
        { ...completeResult, safety: ['One', 'Two', 'Three'] }
    ]) {
        assert.equal(parseSavedReactionResult(JSON.stringify(value)), null);
    }
});

test('partial and blank saved reaction results are rejected', () => {
    for (const value of [
        {},
        { equation: completeResult.equation },
        { ...completeResult, equation: '   ' },
        { ...completeResult, explanation: '' },
        { ...completeResult, safety: '   ' }
    ]) {
        assert.equal(parseSavedReactionResult(JSON.stringify(value)), null);
    }
});

test('saved reaction results require exactly three non-empty safety rules', () => {
    for (const safety of [
        'Wear eye protection.',
        'Wear eye protection. | Keep sodium dry.',
        'Wear eye protection. | Keep sodium dry. | Use supervision. | Stand back.',
        'Wear eye protection. | | Use supervision.'
    ]) {
        assert.equal(
            parseSavedReactionResult(JSON.stringify({ ...completeResult, safety })),
            null
        );
    }
});

test('a complete saved reaction result is preserved', () => {
    assert.deepEqual(
        parseSavedReactionResult(JSON.stringify(completeResult)),
        completeResult
    );
});

test('unsupported saved effects use the existing no-effect boundary', () => {
    for (const effect of [undefined, null, 'smoke', 'color_change', 2]) {
        const value = { ...completeResult, effect };
        assert.deepEqual(
            parseSavedReactionResult(JSON.stringify(value)),
            { ...value, effect: 'none' }
        );
    }
});

test('saved precipitates preserve only allowlisted colors', () => {
    for (const precipitate_color of ['#5ba7d1', '#f2c94c', '#f5f3ea']) {
        const value = {
            ...completeResult,
            effect: 'precipitate',
            precipitate_color
        };
        assert.deepEqual(
            parseSavedReactionResult(JSON.stringify(value)),
            value
        );
    }
});

test('malformed saved precipitates become no effect before restoration', () => {
    for (const precipitate_color of [undefined, null, 'yellow', '#ffffff', 2]) {
        const value = {
            ...completeResult,
            effect: 'precipitate',
            precipitate_color
        };
        assert.deepEqual(
            parseSavedReactionResult(JSON.stringify(value)),
            {
                equation: value.equation,
                explanation: value.explanation,
                safety: value.safety,
                effect: 'none'
            }
        );
    }
});

test('non-precipitate effects discard precipitate colors', () => {
    const value = {
        ...completeResult,
        precipitate_color: '#f5f3ea'
    };
    assert.deepEqual(
        parseSavedReactionResult(JSON.stringify(value)),
        completeResult
    );
});
