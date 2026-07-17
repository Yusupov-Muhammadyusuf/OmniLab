type AnalyticsProperty = string | number | boolean;

declare global {
    interface Window {
        posthog?: {
            capture?: (event: string, properties?: Record<string, AnalyticsProperty>) => void;
        };
    }
}

export function capture(
    event: string,
    properties: Record<string, AnalyticsProperty> = {}
): void {
    window.posthog?.capture?.(event, properties);
}
