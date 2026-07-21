import test from 'node:test';
import assert from 'node:assert/strict';

const supportedPairs = [
    ['Na', 'Cl2'],
    ['H2', 'O2'],
    ['C', 'O2'],
    ['HCl', 'NaOH'],
    ['Fe', 'HCl'],
    ['Cu', 'O2'],
    ['Fe', 'O2'],
    ['CO2', 'NaOH'],
    ['H2', 'Cl2'],
    ['Na', 'H2O'],
    ['CO2', 'H2O'],
    ['NaCl', 'H2O'],
    ['NH3', 'HNO3'],
    ['H2SO4', 'KOH'],
    ['CH3COOH', 'NaHCO3'],
    ['Ca(OH)2', 'CO2'],
    ['CuSO4', 'KOH'],
    ['AgNO3', 'NaCl'],
    ['AgNO3', 'KI'],
    ['KMnO4', 'H2O2'],
    ['Na2CO3', 'HCl'],
    ['BaCl2', 'Na2CO3'],
    ['Zn', 'HCl']
];

globalThis.document = {
    getElementById: () => null
};
globalThis.window = {
    reactionDemo: null,
    supportedReactionPairs: supportedPairs
};

const {
    getCompatibleReactionPartners,
    hasMatchingReactionGuides,
    isSupportedReactionSetup,
    updateLabState
} = await import('../static/js/configuration/config.js');
const { refreshChemicalMenuGuidance } = await import(
    '../static/js/userInterface/ui.js'
);

test('every supported pair is discoverable from either first selection', () => {
    for (const [firstChemical, secondChemical] of supportedPairs) {
        assert.ok(
            getCompatibleReactionPartners(firstChemical).includes(secondChemical),
            `${secondChemical} should be marked after selecting ${firstChemical}`
        );
        assert.ok(
            getCompatibleReactionPartners(secondChemical).includes(firstChemical),
            `${firstChemical} should be marked after selecting ${secondChemical}`
        );
    }
});

test('partner guidance uses the same matrix as Analyze eligibility', () => {
    const supportedKeys = new Set(
        supportedPairs.map(pair => [...pair].sort().join('+'))
    );
    const chemicalIds = [...new Set(supportedPairs.flat())];

    for (const firstChemical of chemicalIds) {
        for (const secondChemical of chemicalIds) {
            if (firstChemical === secondChemical) continue;
            const isMarked = getCompatibleReactionPartners(firstChemical)
                .includes(secondChemical);
            const isSupported = isSupportedReactionSetup([
                firstChemical,
                secondChemical
            ]);
            const key = [firstChemical, secondChemical].sort().join('+');

            assert.equal(isMarked, supportedKeys.has(key));
            assert.equal(isMarked, isSupported);
        }
    }
});

test('only sodium and chlorine have matching study guides', () => {
    assert.equal(hasMatchingReactionGuides(['Na', 'Cl2']), true);
    assert.equal(hasMatchingReactionGuides(['Cl2', 'Na']), true);

    for (const pair of supportedPairs.slice(1)) {
        assert.equal(
            hasMatchingReactionGuides(pair),
            false,
            `${pair.join(' + ')} should not show sodium and chlorine guides`
        );
    }

    for (const invalidSetup of [[], ['Na'], ['Na', 'Cl2', 'H2O']]) {
        assert.equal(hasMatchingReactionGuides(invalidSetup), false);
    }
});

test('a first selection marks every partner and announces the next step', () => {
    class FakeClassList {
        values = new Set();

        toggle(name, enabled) {
            if (enabled) this.values.add(name);
            else this.values.delete(name);
        }

        contains(name) {
            return this.values.has(name);
        }
    }

    class FakeCard {
        constructor(chemicalId) {
            this.attributes = new Map([['data-name', chemicalId]]);
            this.classList = new FakeClassList();
            this.status = { hidden: true, textContent: '' };
        }

        getAttribute(name) {
            return this.attributes.get(name) || null;
        }

        setAttribute(name, value) {
            this.attributes.set(name, value);
        }

        querySelector(selector) {
            return selector === '.chemical-card-status' ? this.status : null;
        }
    }

    const catalog = [
        { id: 'Na', name: 'Sodium', color: '#e09f25' },
        { id: 'Cl2', name: 'Chlorine', color: '#89a83b' },
        { id: 'H2O', name: 'Water', color: '#2b9ed8' },
        { id: 'Cu', name: 'Copper', color: '#b86938' }
    ];
    const cards = catalog.map(chemical => new FakeCard(chemical.id));
    const guidance = { textContent: '' };
    globalThis.document.getElementById = id => (
        id === 'chemical-partner-guidance' ? guidance : null
    );
    globalThis.document.querySelectorAll = selector => (
        selector === '.chemical-card' ? cards : []
    );

    updateLabState({ chemicalDatabase: catalog, selectedChemicals: ['Na'] });
    refreshChemicalMenuGuidance();

    assert.equal(
        guidance.textContent,
        'Choose a partner for Sodium. 2 supported options are marked below.'
    );
    assert.deepEqual(
        cards
            .filter(card => card.classList.contains('compatible-partner'))
            .map(card => card.getAttribute('data-name')),
        ['Cl2', 'H2O']
    );
    assert.match(
        cards[1].getAttribute('aria-label'),
        /Compatible with Sodium/
    );
    assert.equal(cards[0].status.textContent, 'Selected');
    assert.equal(cards[1].status.textContent, 'Compatible');
    assert.equal(cards[3].status.hidden, true);
});
