export const canvas = document.getElementById('lab-canvas');
export const ctx = canvas ? canvas.getContext('2d') : null;
const GUIDE_VISIT_SOURCES = new Set([
    'guide_reaction',
    'guide_formula',
    'guide_ionic_bond'
]);
const ALLOWED_VISIT_SOURCES = new Set([
    'student_invite',
    ...GUIDE_VISIT_SOURCES
]);
const supportedReactionPairs = window.supportedReactionPairs || [['Na', 'Cl2']];
const supportedReactionPairKeys = new Set(supportedReactionPairs.map(pair => [...pair].sort().join('+')));
const reactionGuidePairKeys = new Set(['Cl2+Na']);
const supportedChemicalIds = new Set(supportedReactionPairs.flat());
const supportedReactionPartners = new Map();
for (const [firstChemical, secondChemical] of supportedReactionPairs) {
    const firstPartners = supportedReactionPartners.get(firstChemical) || new Set();
    const secondPartners = supportedReactionPartners.get(secondChemical) || new Set();
    firstPartners.add(secondChemical);
    secondPartners.add(firstChemical);
    supportedReactionPartners.set(firstChemical, firstPartners);
    supportedReactionPartners.set(secondChemical, secondPartners);
}
let state = {
    chemicalDatabase: [],
    selectedChemicals: [],
    currentVessel: 'flask',
    theme: 'light',
    targetLiquidVol: 0,
    currentLiquidVol: 0,
    liquidColor: '#3399ff',
    waveTime: 0,
    streamActive: false,
    streamX: 0,
    streamColor: '#ffffff',
    splashParticles: [],
    ambientBubbles: [],
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
    vesselOffsetX: 0,
    vesselOffsetY: 0,
    smokeParticles: [],
    explosionParticles: [],
    isBubbling: false,
    burnerActive: false
};
export function getLabState() {
    return state;
}
export function updateLabState(newState) {
    state = { ...state, ...newState };
}
export function getReactionDemoConfig() {
    return window.reactionDemo || null;
}
export function getGuideVisitSource(source) {
    return source && GUIDE_VISIT_SOURCES.has(source)
        ? source
        : null;
}
export function getVisitSource() {
    if (!getReactionDemoConfig())
        return null;
    const source = new URLSearchParams(window.location.search).get('source');
    return source && ALLOWED_VISIT_SOURCES.has(source)
        ? source
        : null;
}
export function isSupportedReactionSetup(selectedChemicals) {
    if (selectedChemicals.length !== 2)
        return false;
    return supportedReactionPairKeys.has([...selectedChemicals].sort().join('+'));
}
export function hasMatchingReactionGuides(selectedChemicals) {
    if (selectedChemicals.length !== 2)
        return false;
    return reactionGuidePairKeys.has([...selectedChemicals].sort().join('+'));
}
export function getCompatibleReactionPartners(chemicalId) {
    return [...(supportedReactionPartners.get(chemicalId) || [])];
}
export function parseSavedChemicals(serializedChemicals) {
    if (serializedChemicals === null)
        return null;
    try {
        const parsedChemicals = JSON.parse(serializedChemicals);
        if (!Array.isArray(parsedChemicals))
            return null;
        if (!parsedChemicals.every((chemical) => typeof chemical === 'string'
            && supportedChemicalIds.has(chemical)))
            return null;
        if (new Set(parsedChemicals).size !== parsedChemicals.length)
            return null;
        return parsedChemicals;
    }
    catch {
        return null;
    }
}
export function getLabStorageKey(baseKey) {
    const reactionDemo = getReactionDemoConfig();
    return reactionDemo
        ? `reactionDemo:${reactionDemo.id}:${baseKey}`
        : baseKey;
}
export function hexToRgbA(hex, alpha = 1) {
    let c;
    if (/^#([A-Fa-f0-9]{3}){1,2}$/.test(hex)) {
        c = hex.substring(1).split('');
        if (c.length === 3) {
            c = [c[0], c[0], c[1], c[1], c[2], c[2]];
        }
        const num = parseInt(c.join(''), 16);
        return `rgba(${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}, ${alpha})`;
    }
    return `rgba(0, 0, 0, ${alpha})`;
}
//# sourceMappingURL=config.js.map