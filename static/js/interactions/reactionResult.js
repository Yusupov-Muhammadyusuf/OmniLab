const SUPPORTED_REACTION_EFFECTS = new Set([
    'explosion',
    'bubble',
    'precipitate',
    'none'
]);
const SUPPORTED_PRECIPITATE_COLORS = new Set([
    '#5ba7d1',
    '#f2c94c',
    '#f5f3ea'
]);
export function normalizePrecipitateColor(effect, color) {
    return effect === 'precipitate'
        && SUPPORTED_PRECIPITATE_COLORS.has(color)
        ? color
        : undefined;
}
export function normalizeReactionEffect(effect, precipitateColor) {
    if (effect === 'precipitate') {
        return normalizePrecipitateColor(effect, precipitateColor)
            ? 'precipitate'
            : 'none';
    }
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
        const effect = normalizeReactionEffect(candidate.effect, candidate.precipitate_color);
        const precipitateColor = normalizePrecipitateColor(effect, candidate.precipitate_color);
        return {
            equation,
            explanation,
            safety,
            effect,
            ...(precipitateColor
                ? { precipitate_color: precipitateColor }
                : {})
        };
    }
    catch {
        return null;
    }
}
//# sourceMappingURL=reactionResult.js.map
