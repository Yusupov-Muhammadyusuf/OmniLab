let labSetupCaptured = false;
export function capture(event, properties = {}) {
    window.posthog?.capture?.(event, properties);
}
export function captureLabSetupStarted(properties) {
    if (labSetupCaptured)
        return;
    labSetupCaptured = true;
    capture('lab_setup_started', properties);
}
//# sourceMappingURL=analytics.js.map