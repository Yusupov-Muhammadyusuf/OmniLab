import { capture } from '../analytics/analytics.js';
import { getGuideVisitSource } from '../configuration/config.js';
document.addEventListener('DOMContentLoaded', () => {
    const visitSource = getGuideVisitSource(window.guideVisitSource || null);
    if (!visitSource)
        return;
    capture('chemistry_guide_entered', { visit_source: visitSource });
});
//# sourceMappingURL=guide.js.map