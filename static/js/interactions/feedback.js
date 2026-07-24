const FEEDBACK_EMAIL_ADDRESS = 'omnilab-bk8q@mail.tin.computer';
const FEEDBACK_PROMPTS = [
    'What were you trying to predict?',
    'What do you plan to do next?'
].join('\n\n');
const FEEDBACK_GUIDE_LABELS = {
    guide_reaction: 'Reaction guide',
    guide_formula: 'Formula guide',
    guide_ionic_bond: 'Ionic bond guide'
};
export function buildFeedbackMailtoUrl(source) {
    const guideLabel = source
        && Object.prototype.hasOwnProperty.call(FEEDBACK_GUIDE_LABELS, source)
        ? FEEDBACK_GUIDE_LABELS[source]
        : null;
    const feedbackBody = guideLabel
        ? [`Guide source: ${guideLabel}`, FEEDBACK_PROMPTS].join('\n\n')
        : FEEDBACK_PROMPTS;
    return `mailto:${FEEDBACK_EMAIL_ADDRESS}?body=${encodeURIComponent(feedbackBody)}`;
}
//# sourceMappingURL=feedback.js.map