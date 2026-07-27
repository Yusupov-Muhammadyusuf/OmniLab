import { capture } from '../analytics/analytics.js';

const feedbackEvents = new Set([
    'reaction_feedback_viewed',
    'reaction_feedback_accepted',
    'reaction_feedback_validation_failed',
    'reaction_feedback_rate_limited',
    'reaction_feedback_delivery_failed',
]);
const feedbackEvent = document.body.dataset.feedbackEvent;

if (feedbackEvent && feedbackEvents.has(feedbackEvent)) {
    capture(feedbackEvent);
}
