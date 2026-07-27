import { capture } from '../analytics/analytics.js';
const FEEDBACK_SOURCE = 'reaction_feedback';
export function buildFeedbackContactUrl() {
    return `/contact/?source=${FEEDBACK_SOURCE}`;
}
function captureFeedbackOpened() {
    capture('reaction_feedback_opened');
}
export function bindFeedbackOpenCapture(feedbackLink) {
    feedbackLink.onclick = captureFeedbackOpened;
}
//# sourceMappingURL=feedback.js.map