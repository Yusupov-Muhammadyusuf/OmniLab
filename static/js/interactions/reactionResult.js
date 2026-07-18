const SUPPORTED_REACTION_EFFECTS = new Set([
    'explosion',
    'bubble',
    'none'
]);
export function normalizeReactionEffect(effect) {
    return SUPPORTED_REACTION_EFFECTS.has(effect)
        ? effect
        : 'none';
}
function isNonEmptyString(value) {
    return typeof value === 'string' && value.trim().length > 0;
}
export function parseSavedReactionResult(serializedReaction) {
    if (serializedReaction === null)
        return null;
    try {
        const parsedReaction = JSON.parse(serializedReaction);
        if (typeof parsedReaction !== 'object'
            || parsedReaction === null
            || Array.isArray(parsedReaction))
            return null;
        const candidate = parsedReaction;
        const equation = candidate.equation;
        const explanation = candidate.explanation;
        const safety = candidate.safety;
        if (!isNonEmptyString(equation)
            || !isNonEmptyString(explanation)
            || !isNonEmptyString(safety))
            return null;
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
    }
    catch {
        return null;
    }
}
//# sourceMappingURL=reactionResult.js.map
