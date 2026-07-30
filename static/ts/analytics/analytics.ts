import type { LabEntryAttribution } from '../configuration/config.js';

type AnalyticsProperty = string | number | boolean | undefined;
type AnalyticsProperties = Record<string, AnalyticsProperty>;

interface LabSetupProperties extends AnalyticsProperties, LabEntryAttribution {
    vessel: string;
    burner_active: boolean;
}

let labSetupCaptured = false;

declare global {
    interface Window {
        posthog?: {
            capture?: (event: string, properties?: AnalyticsProperties) => void;
        };
    }
}

export function capture(
    event: string,
    properties: AnalyticsProperties = {}
): void {
    window.posthog?.capture?.(event, properties);
}

export function captureLabSetupStarted(properties: LabSetupProperties): void {
    if (labSetupCaptured) return;

    labSetupCaptured = true;
    capture('lab_setup_started', properties);
}
