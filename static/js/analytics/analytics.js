let labSetupCaptured = false;
const CONTROLLED_VERIFICATION_PARAM = 'verification';
const CONTROLLED_VERIFICATION_VALUE = 'controlled';
const VISIT_TYPE_EVENTS = new Set([
    'lab_viewed',
    'reaction_analysis_completed'
]);
export function capture(event, properties = {}) {
    const query = new URLSearchParams(window.location?.search ?? '');
    const isControlledVerification = (query.get(CONTROLLED_VERIFICATION_PARAM) ===
        CONTROLLED_VERIFICATION_VALUE);
    if (isControlledVerification)
        return;
    const tracksVisitType = VISIT_TYPE_EVENTS.has(event);
    const measuredProperties = tracksVisitType
        ? { ...properties, visit_type: 'unclassified' }
        : properties;
    window.posthog?.capture?.(event, measuredProperties);
}
export function captureLabSetupStarted(properties) {
    if (labSetupCaptured)
        return;
    labSetupCaptured = true;
    capture('lab_setup_started', properties);
}
//# sourceMappingURL=analytics.js.map