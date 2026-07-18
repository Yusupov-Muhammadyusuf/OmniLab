export const canvas = document.getElementById('lab-canvas') as HTMLCanvasElement | null;
export const ctx = canvas ? canvas.getContext('2d') : null;

export interface Chemical {
    id: string;
    name: string;
    color: string;
}

export interface Particle {
    x: number;
    y: number;
    vx: number;
    vy: number;
    alpha: number;
    color: string;
}

export interface LabState {
    chemicalDatabase: Chemical[];
    selectedChemicals: string[];
    currentVessel: 'flask' | 'beaker' | 'tube';
    theme: 'light' | 'dark';
    targetLiquidVol: number;
    currentLiquidVol: number;
    liquidColor: string;
    waveTime: number;
    streamActive: boolean;
    streamX: number;
    streamColor: string;
    splashParticles: Particle[];
    ambientBubbles: Particle[];
    isDragging: boolean;
    dragStartX: number;
    dragStartY: number;
    vesselOffsetX: number;
    vesselOffsetY: number;
    smokeParticles: Particle[];
    explosionParticles: Particle[];
    isBubbling: boolean;
    burnerActive: boolean;
}

export interface ReactionDemoConfig {
    id: string;
    version: string;
    selectedChemicals: string[];
    vessel: LabState['currentVessel'];
    liquidColor: string;
}

type SupportedReactionPair = [string, string];

export type GuideVisitSource =
    | 'guide_reaction'
    | 'guide_formula'
    | 'guide_ionic_bond';

export type VisitSource = 'student_invite' | GuideVisitSource;

const GUIDE_VISIT_SOURCES = new Set<GuideVisitSource>([
    'guide_reaction',
    'guide_formula',
    'guide_ionic_bond'
]);

const ALLOWED_VISIT_SOURCES = new Set<VisitSource>([
    'student_invite',
    ...GUIDE_VISIT_SOURCES
]);

declare global {
    interface Window {
        reactionDemo?: ReactionDemoConfig | null;
        supportedReactionPairs?: SupportedReactionPair[];
    }
}

const supportedReactionPairs = window.supportedReactionPairs || [['Na', 'Cl2']];
const supportedReactionPairKeys = new Set(
    supportedReactionPairs.map(pair => [...pair].sort().join('+'))
);
const supportedChemicalIds = new Set(supportedReactionPairs.flat());

let state: LabState = {
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

export function getLabState(): LabState {
    return state;
}

export function updateLabState(newState: Partial<LabState>): void {
    state = { ...state, ...newState };
}

export function getReactionDemoConfig(): ReactionDemoConfig | null {
    return window.reactionDemo || null;
}

export function getGuideVisitSource(source: string | null): GuideVisitSource | null {
    return source && GUIDE_VISIT_SOURCES.has(source as GuideVisitSource)
        ? source as GuideVisitSource
        : null;
}

export function getVisitSource(): VisitSource | null {
    if (!getReactionDemoConfig()) return null;

    const source = new URLSearchParams(window.location.search).get('source');
    return source && ALLOWED_VISIT_SOURCES.has(source as VisitSource)
        ? source as VisitSource
        : null;
}

export function isSupportedReactionSetup(selectedChemicals: string[]): boolean {
    if (selectedChemicals.length !== 2) return false;
    return supportedReactionPairKeys.has([...selectedChemicals].sort().join('+'));
}

export function parseSavedChemicals(serializedChemicals: string | null): string[] | null {
    if (serializedChemicals === null) return null;

    try {
        const parsedChemicals: unknown = JSON.parse(serializedChemicals);
        if (!Array.isArray(parsedChemicals)) return null;
        if (!parsedChemicals.every(
            (chemical: unknown): chemical is string => typeof chemical === 'string'
                && supportedChemicalIds.has(chemical)
        )) return null;
        if (new Set(parsedChemicals).size !== parsedChemicals.length) return null;

        return parsedChemicals;
    } catch {
        return null;
    }
}

export function getLabStorageKey(baseKey: string): string {
    const reactionDemo = getReactionDemoConfig();
    return reactionDemo
        ? `reactionDemo:${reactionDemo.id}:${baseKey}`
        : baseKey;
}

export function hexToRgbA(hex: string, alpha: number = 1): string {
    let c: string[] | null;
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
