import * as config from '../configuration/config.js';
import { closeAllPopovers } from '../userInterface/ui.js';
import { drawVesselAndFluid, triggerSmokeEffect, triggerThermalBlast } from '../rendering/render.js';
import { capture, captureLabSetupStarted } from '../analytics/analytics.js';
export function setupCanvasDrag() {
    if (!config.canvas)
        return;
    config.canvas.addEventListener('mousedown', function (e) {
        if (!config.canvas)
            return;
        const rect = config.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const state = config.getLabState();
        let cx = config.canvas.width / 2 + state.vesselOffsetX;
        let cy = config.canvas.height / 2 + 50 + state.vesselOffsetY;
        let checkCy = state.burnerActive ? cy - 40 : cy;
        let btnX = cx;
        let btnY = checkCy + 110 + 48;
        let dist = Math.sqrt((mouseX - btnX) ** 2 + (mouseY - btnY) ** 2);
        if (dist <= 12) {
            config.updateLabState({ burnerActive: !state.burnerActive });
            drawVesselAndFluid();
            return;
        }
        const currentCy = state.burnerActive ? cy - 40 : cy;
        let clickRadius = state.currentVessel === 'flask' ? 110 : (state.currentVessel === 'beaker' ? 90 : 40);
        if (Math.abs(mouseX - cx) < clickRadius && mouseY > currentCy - 100 && mouseY < currentCy + 110) {
            config.updateLabState({
                isDragging: true,
                dragStartX: e.clientX,
                dragStartY: e.clientY
            });
        }
    });
    window.addEventListener('mousemove', function (e) {
        const state = config.getLabState();
        if (!state.isDragging)
            return;
        const dx = e.clientX - state.dragStartX;
        const dy = e.clientY - state.dragStartY;
        config.updateLabState({
            vesselOffsetX: state.vesselOffsetX + dx,
            vesselOffsetY: state.vesselOffsetY + dy,
            dragStartX: e.clientX,
            dragStartY: e.clientY
        });
    });
    window.addEventListener('mouseup', function () {
        config.updateLabState({ isDragging: false });
    });
}
export function allowDrop(ev) {
    ev.preventDefault();
}
export function drop(ev) {
    ev.preventDefault();
    if (!config.canvas || !ev.dataTransfer)
        return;
    const rect = config.canvas.getBoundingClientRect();
    config.updateLabState({ streamX: ev.clientX - rect.left });
    const id = ev.dataTransfer.getData("text");
    const element = document.getElementById(id);
    if (!element)
        return;
    const name = element.getAttribute('data-name');
    const color = element.getAttribute('data-color');
    if (!name || !color)
        return;
    const state = config.getLabState();
    if (!state.selectedChemicals.includes(name)) {
        const updatedChemicals = [...state.selectedChemicals, name];
        const targetVol = Math.min(updatedChemicals.length * 30, 210);
        config.updateLabState({
            selectedChemicals: updatedChemicals,
            liquidColor: color,
            streamColor: color,
            streamActive: true,
            targetLiquidVol: targetVol
        });
        if (updatedChemicals.length === 1) {
            captureLabSetupStarted({
                vessel: state.currentVessel,
                burner_active: state.burnerActive
            });
        }
        localStorage.setItem('savedChemicals', JSON.stringify(updatedChemicals));
        localStorage.setItem('savedLiquidColor', color);
        const mixtureEl = document.getElementById('current-mixture');
        if (mixtureEl) {
            mixtureEl.innerText = updatedChemicals.join(' + ');
        }
    }
    closeAllPopovers();
}
export function resetLaboratory() {
    localStorage.removeItem('savedChemicals');
    localStorage.removeItem('savedLiquidColor');
    config.updateLabState({
        selectedChemicals: [],
        targetLiquidVol: 0,
        currentLiquidVol: 0,
        splashParticles: [],
        ambientBubbles: [],
        smokeParticles: [],
        explosionParticles: [],
        isBubbling: false,
        streamActive: false,
        vesselOffsetX: 0,
        vesselOffsetY: 0
    });
    const mixtureEl = document.getElementById('current-mixture');
    if (mixtureEl) {
        mixtureEl.innerText = "Empty Vessel";
    }
    drawVesselAndFluid();
}
export function fireAIAnalysis() {
    const state = config.getLabState();
    if (state.selectedChemicals.length === 0) {
        alert("Laboratory apparatus matrix is currently empty!");
        return;
    }
    const panel = document.getElementById('ai-response-content');
    if (!panel)
        return;
    const analysisStartedAt = performance.now();
    capture('reaction_analysis_started', {
        chemical_count: state.selectedChemicals.length,
        vessel: state.currentVessel,
        burner_active: state.burnerActive
    });
    panel.innerHTML = '<div class="text-center mt-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2 fw-bold text-body-secondary">Analyzing chemical reaction...</p></div>';
    let formData = new FormData();
    formData.append('query', state.selectedChemicals.join(' + '));
    fetch('/ai_insights/', {
        method: 'POST',
        body: formData
    })
        .then(res => res.text())
        .then(rawText => {
        const cleanedText = rawText.replace(/[\n\r\t]/g, ' ');
        const resData = JSON.parse(cleanedText);
        if (resData.status === 'success') {
            capture('reaction_analysis_completed', {
                chemical_count: state.selectedChemicals.length,
                vessel: state.currentVessel,
                effect: resData.data.effect,
                duration_ms: Math.round(performance.now() - analysisStartedAt)
            });
            localStorage.setItem('savedReaction', JSON.stringify(resData.data));
            const reaction = resData.data;
            const safetyPoints = reaction.safety.split('|').map(p => p.trim()).filter(p => p.length > 0);
            const safetyHTML = safetyPoints.map(p => `<li class="mb-2"><i class="bi bi-shield-exclamation me-2"></i>${p}</li>`).join('');
            panel.innerHTML = `
                <div class="lh-base spectrum-analysis-log animate__animated animate__fadeIn text-body-emphasis" style="font-family: 'UbuntuLocal', sans-serif; font-size: 16px; line-height: 1.6; letter-spacing: 0.3px;">

                    <div class="mb-4 core-equation-block p-3 bg-dark text-white rounded-4 shadow-lg border border-secondary border-opacity-25">
                        <h6 class="text-white-50 text-uppercase small fw-bold mb-2" style="letter-spacing: 1.5px;">
                            <i class="bi bi-mortar-pestle me-2 text-info"></i>Chemical Equation Formula
                        </h6>
                        <div class="fs-5 text-center py-2 px-2 text-white border border-secondary border-opacity-50 rounded-3"
                            style="font-family: 'Fira Code', monospace; font-weight: 500; background-color: #1e1e24; letter-spacing: 1.5px;">
                            ${reaction.equation}
                        </div>
                    </div>

                    <div class="mb-4 conceptual-breakdown px-2">
                        <h6 class="text-body-secondary text-uppercase small fw-bold mb-2">
                            <i class="bi bi-file-earmark-text me-2 text-info"></i>Analysis
                        </h6>
                        <div class="text-body-emphasis" style="text-align: justify; text-justify: inter-word;">
                            ${reaction.explanation}
                        </div>
                    </div>

                    <div class="alert alert-warning bg-warning-subtle border-warning border-start border-5 shadow-sm p-3 safety-matrix-block rounded-end">
                        <h6 class="text-secondary text-uppercase small fw-bold mb-2">
                            <i class="bi bi-exclamation-triangle-fill me-2 text-warning"></i>Safety rules
                        </h6>
                        <ul class="list-unstyled mb-0 small text-secondary fw-medium">
                            ${safetyHTML || `<li>${reaction.safety}</li>`}
                        </ul>
                    </div>

                </div>
            `;
            config.updateLabState({ isBubbling: false });
            if (reaction.effect === 'explosion') {
                triggerThermalBlast();
            }
            else if (reaction.effect === 'smoke') {
                triggerSmokeEffect();
            }
            else if (reaction.effect === 'color_change' && reaction.new_color !== 'none') {
                config.updateLabState({ liquidColor: reaction.new_color });
                localStorage.setItem('savedLiquidColor', reaction.new_color);
            }
            else if (reaction.effect === 'bubble') {
                const currentState = config.getLabState();
                config.updateLabState({
                    isBubbling: true,
                    targetLiquidVol: Math.min(currentState.targetLiquidVol + 40, 210)
                });
            }
        }
        else {
            capture('reaction_analysis_failed', {
                stage: 'response',
                duration_ms: Math.round(performance.now() - analysisStartedAt)
            });
            panel.innerHTML = `<div class="alert alert-danger bg-danger-subtle text-danger-emphasis border-danger">Processing Fault: ${resData.message}</div>`;
        }
    })
        .catch(err => {
        capture('reaction_analysis_failed', {
            stage: 'network_or_parse',
            duration_ms: Math.round(performance.now() - analysisStartedAt)
        });
        panel.innerHTML = `<div class="alert alert-danger bg-danger-subtle text-danger-emphasis border-danger">Network Runtime Error: ${err.message}</div>`;
    });
}
document.addEventListener("DOMContentLoaded", () => {
    const savedChemicals = localStorage.getItem('savedChemicals');
    const savedLiquidColor = localStorage.getItem('savedLiquidColor');
    if (savedChemicals) {
        const chemicals = JSON.parse(savedChemicals);
        config.updateLabState({ selectedChemicals: chemicals });
        const mixtureEl = document.getElementById('current-mixture');
        if (mixtureEl) {
            mixtureEl.innerText = chemicals.join(' + ');
        }
        const vol = Math.min(chemicals.length * 30, 210);
        config.updateLabState({
            targetLiquidVol: vol,
            currentLiquidVol: vol
        });
    }
    else {
        const mixtureEl = document.getElementById('current-mixture');
        if (mixtureEl) {
            mixtureEl.innerText = "Empty Vessel";
        }
    }
    if (savedLiquidColor) {
        config.updateLabState({ liquidColor: savedLiquidColor });
    }
    if (savedChemicals || savedLiquidColor) {
        drawVesselAndFluid();
    }
    const savedData = localStorage.getItem('savedReaction');
    if (savedData) {
        try {
            const reaction = JSON.parse(savedData);
            const panel = document.getElementById('ai-response-content');
            if (!panel)
                return;
            const safetyPoints = reaction.safety.split('|').map((p) => p.trim()).filter((p) => p.length > 0);
            const safetyHTML = safetyPoints.map((p) => `<li class="mb-2"><i class="bi bi-shield-exclamation me-2"></i>${p}</li>`).join('');
            panel.innerHTML = `
                <div class="lh-base spectrum-analysis-log animate__animated animate__fadeIn text-body-emphasis" style="font-family: 'UbuntuLocal', sans-serif; font-size: 16px; line-height: 1.6; letter-spacing: 0.3px;">

                    <div class="mb-4 core-equation-block p-3 bg-dark text-white rounded-4 shadow-lg border border-secondary border-opacity-25">
                        <h6 class="text-white-50 text-uppercase small fw-bold mb-2" style="letter-spacing: 1.5px;">
                            <i class="bi bi-mortar-pestle me-2 text-info"></i>Chemical Equation Formula
                        </h6>
                        <div class="fs-5 text-center py-2 px-2 text-white border border-secondary border-opacity-50 rounded-3"
                            style="font-family: 'Fira Code', monospace; font-weight: 500; background-color: #1e1e24; letter-spacing: 1.5px;">
                            ${reaction.equation}
                        </div>
                    </div>

                    <div class="mb-4 conceptual-breakdown px-2">
                        <h6 class="text-body-secondary text-uppercase small fw-bold mb-2">
                            <i class="bi bi-file-earmark-text me-2 text-info"></i>Analysis
                        </h6>
                        <div class="text-body-emphasis" style="text-align: justify; text-justify: inter-word;">
                            ${reaction.explanation}
                        </div>
                    </div>

                    <div class="alert alert-warning bg-warning-subtle border-warning border-start border-5 shadow-sm p-3 safety-matrix-block rounded-end">
                        <h6 class="text-secondary text-uppercase small fw-bold mb-2">
                            <i class="bi bi-exclamation-triangle-fill me-2 text-warning"></i>Safety rules
                        </h6>
                        <ul class="list-unstyled mb-0 small text-secondary fw-medium">
                            ${safetyHTML || `<li>${reaction.safety}</li>`}
                        </ul>
                    </div>

                </div>
            `;
        }
        catch (e) {
            localStorage.removeItem('savedReaction');
        }
    }
    else {
        const panel = document.getElementById('ai-response-content');
        if (panel) {
            panel.innerHTML = '<p class="text-center mt-5" style="opacity: 0.6;">Introduce elements into the vessel from the floating core menu, then trigger analytical mapping.</p>';
        }
    }
});
//# sourceMappingURL=interactions.js.map