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
const SUPPORTED_REACTION_CHEMICALS = new Set(['Na', 'Cl2']);
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
    return selectedChemicals.length === SUPPORTED_REACTION_CHEMICALS.size
        && selectedChemicals.every(chemical => SUPPORTED_REACTION_CHEMICALS.has(chemical));
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
