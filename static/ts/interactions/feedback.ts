const FEEDBACK_SOURCE = 'reaction_feedback';

export function buildFeedbackContactUrl(): string {
    return `/contact/?source=${FEEDBACK_SOURCE}`;
}
