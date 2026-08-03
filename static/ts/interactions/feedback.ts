import { capture } from '../analytics/analytics.js';

const FEEDBACK_SOURCE = 'reaction_feedback';
const viewedFeedbackPrompts = new WeakSet<HTMLAnchorElement>();

export function buildFeedbackContactUrl(): string {
    return `/contact/?source=${FEEDBACK_SOURCE}`;
}

function captureFeedbackOpened(): void {
    capture('reaction_feedback_opened');
}

export function captureFeedbackPromptViewed(
    feedbackLink: HTMLAnchorElement
): void {
    if (viewedFeedbackPrompts.has(feedbackLink)) return;

    viewedFeedbackPrompts.add(feedbackLink);
    capture('reaction_feedback_prompt_viewed');
}

export function bindFeedbackOpenCapture(
    feedbackLink: HTMLAnchorElement
): void {
    feedbackLink.onclick = captureFeedbackOpened;
}
