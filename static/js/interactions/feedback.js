import { capture } from '../analytics/analytics.js';
const FEEDBACK_SOURCE = 'reaction_feedback';
const viewedFeedbackPrompts = new WeakSet();
export function buildFeedbackContactUrl() {
    return `/contact/?source=${FEEDBACK_SOURCE}`;
}
function captureFeedbackOpened() {
    capture('reaction_feedback_opened');
}
export function captureFeedbackPromptViewed(feedbackLink) {
    if (viewedFeedbackPrompts.has(feedbackLink))
        return;
    viewedFeedbackPrompts.add(feedbackLink);
    capture('reaction_feedback_prompt_viewed');
}
export function bindFeedbackOpenCapture(feedbackLink) {
    feedbackLink.onclick = captureFeedbackOpened;
}
//# sourceMappingURL=feedback.js.map