export type SupportedReactionEffect = 'explosion' | 'bubble' | 'none';

export interface ReactionResult {
    equation: string;
    explanation: string;
    safety: string;
    effect: SupportedReactionEffect;
}

const SUPPORTED_REACTION_EFFECTS = new Set<SupportedReactionEffect>([
    'explosion',
    'bubble',
    'none'
]);

export function normalizeReactionEffect(effect: unknown): SupportedReactionEffect {
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

        return {
            equation,
            explanation,
            safety,
            effect: normalizeReactionEffect(candidate.effect)
        };
    } catch {
        return null;
    }
}
