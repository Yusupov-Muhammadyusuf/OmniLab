export type SupportedReactionEffect = 'explosion' | 'bubble' | 'precipitate' | 'none';
export type SupportedPrecipitateColor = '#5ba7d1' | '#f2c94c' | '#f5f3ea';

export interface ReactionResult {
    equation: string;
    explanation: string;
    safety: string;
    effect: SupportedReactionEffect;
    precipitate_color?: SupportedPrecipitateColor;
}

const SUPPORTED_REACTION_EFFECTS = new Set<SupportedReactionEffect>([
    'explosion',
    'bubble',
    'precipitate',
    'none'
]);
const SUPPORTED_PRECIPITATE_COLORS = new Set<SupportedPrecipitateColor>([
    '#5ba7d1',
    '#f2c94c',
    '#f5f3ea'
]);

export function normalizePrecipitateColor(
    effect: unknown,
    color: unknown
): SupportedPrecipitateColor | undefined {
    return effect === 'precipitate'
        && SUPPORTED_PRECIPITATE_COLORS.has(color as SupportedPrecipitateColor)
        ? color as SupportedPrecipitateColor
        : undefined;
}

export function normalizeReactionEffect(
    effect: unknown,
    precipitateColor?: unknown
): SupportedReactionEffect {
    if (effect === 'precipitate') {
        return normalizePrecipitateColor(effect, precipitateColor)
            ? 'precipitate'
            : 'none';
    }
    return SUPPORTED_REACTION_EFFECTS.has(effect as SupportedReactionEffect)
        ? effect as SupportedReactionEffect
        : 'none';
}

function isNonEmptyString(value: unknown): value is string {
    return typeof value === 'string' && value.trim().length > 0;
}

export function parseSavedReactionResult(serializedReaction: string | null): ReactionResult | null {
    if (serializedReaction === null) return null;

    try {
        const parsedReaction: unknown = JSON.parse(serializedReaction);
        if (
            typeof parsedReaction !== 'object'
            || parsedReaction === null
            || Array.isArray(parsedReaction)
        ) return null;

        const candidate = parsedReaction as Record<string, unknown>;
        const equation = candidate.equation;
        const explanation = candidate.explanation;
        const safety = candidate.safety;
        if (
            !isNonEmptyString(equation)
            || !isNonEmptyString(explanation)
            || !isNonEmptyString(safety)
        ) return null;

        const safetyRules = safety.split('|').map(rule => rule.trim());
        if (safetyRules.length !== 3 || !safetyRules.every(rule => rule.length > 0)) {
            return null;
        }

        const effect = normalizeReactionEffect(
            candidate.effect,
            candidate.precipitate_color
        );
        const precipitateColor = normalizePrecipitateColor(
            effect,
            candidate.precipitate_color
        );

        return {
            equation,
            explanation,
            safety,
            effect,
            ...(precipitateColor
                ? { precipitate_color: precipitateColor }
                : {})
        };
    } catch {
        return null;
    }
}
