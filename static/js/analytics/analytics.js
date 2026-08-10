let labSetupCaptured = false;
const CONTROLLED_VERIFICATION_PARAM = 'verification';
const CONTROLLED_VERIFICATION_VALUE = 'controlled';
const STUDENT_INVITE_SOURCE = 'student_invite';
export function capture(event, properties = {}) {
    const query = new URLSearchParams(window.location?.search ?? '');
    const isControlledVerification = (query.get(CONTROLLED_VERIFICATION_PARAM) ===
        CONTROLLED_VERIFICATION_VALUE &&
        query.get('source') !== STUDENT_INVITE_SOURCE);
    if (isControlledVerification)
        return;
    window.posthog?.capture?.(event, properties);
}
export function captureLabSetupStarted(properties) {
    if (labSetupCaptured)
        return;
    labSetupCaptured = true;
    capture('lab_setup_started', properties);
}
//# sourceMappingURL=analytics.js.map