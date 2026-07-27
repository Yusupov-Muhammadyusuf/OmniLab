import { capture } from '../analytics/analytics.js';

const FEEDBACK_SOURCE = 'reaction_feedback';

export function buildFeedbackContactUrl(): string {
    return `/contact/?source=${FEEDBACK_SOURCE}`;
}

function captureFeedbackOpened(): void {
    capture('reaction_feedback_opened');
}

export function bindFeedbackOpenCapture(
    feedbackLink: HTMLAnchorElement
): void {
    feedbackLink.onclick = captureFeedbackOpened;
}
