import { capture } from '../analytics/analytics.js';
import { getGuideVisitSource } from '../configuration/config.js';

declare global {
    interface Window {
        guideVisitSource?: string;
    }
}

document.addEventListener('DOMContentLoaded', (): void => {
    const visitSource = getGuideVisitSource(window.guideVisitSource || null);
    if (!visitSource) return;

    capture('chemistry_guide_entered', { visit_source: visitSource });
});
