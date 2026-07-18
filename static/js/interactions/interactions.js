import * as config from '../configuration/config.js';
import { closeAllPopovers } from '../userInterface/ui.js';
import { cancelReactionEffects, drawVesselAndFluid, triggerSmokeEffect, triggerThermalBlast } from '../rendering/render.js';
import { capture, captureLabSetupStarted } from '../analytics/analytics.js';
const DEFAULT_REACTION_INSTRUCTION = `
    <div class="text-center mt-5 lab-empty-state">
        <p class="lab-instruction mb-2">Start with <strong>Sodium and Chlorine</strong>, OmniLab's supported pair. Add both from Chemicals.</p>
        <a class="lab-demo-link" href="/demo/sodium-chlorine/">
            Open the prepared demo
            <i class="bi bi-arrow-right" aria-hidden="true"></i>
        </a>
    </div>
`;
const DEMO_REACTION_INSTRUCTION = '<p class="text-center mt-5 lab-instruction">This setup is ready. Select Analyze Chemical Reaction to request the prediction.</p>';
const FEEDBACK_EMAIL_ADDRESS = 'omnilab-bk8q@mail.tin.computer';
const FEEDBACK_PROMPTS = [
    'What were you trying to predict?',
    'What do you plan to do next?'
].join('\n\n');
let activeAnalysisController = null;
let currentAnalysisRunId = 0;
function setAnalysisPending(pending) {
    const analyzeBtn = document.getElementById('btn-fire-analysis');
    if (!analyzeBtn)
        return;
    analyzeBtn.disabled = pending;
    analyzeBtn.setAttribute('aria-busy', pending ? 'true' : 'false');
}
function buildFeedbackMailtoUrl() {
    return `mailto:${FEEDBACK_EMAIL_ADDRESS}?body=${encodeURIComponent(FEEDBACK_PROMPTS)}`;
}
export function renderReactionResult(panel, reaction) {
    panel.innerHTML = `
        <div class="lh-base spectrum-analysis-log animate__animated animate__fadeIn text-body-emphasis" style="font-family: 'UbuntuLocal', sans-serif; font-size: 16px; line-height: 1.6; letter-spacing: 0.3px;">

            <div class="mb-4 core-equation-block p-3 bg-dark text-white rounded-4 shadow-lg border border-secondary border-opacity-25">
                <h3 class="h6 text-white-50 text-uppercase small fw-bold mb-2" style="letter-spacing: 1.5px;">
                    <i class="bi bi-mortar-pestle me-2 text-info"></i>Chemical Equation Formula
                </h3>
                <div class="fs-5 text-center py-2 px-2 text-white border border-secondary border-opacity-50 rounded-3 reaction-equation"
                    style="font-family: 'Fira Code', monospace; font-weight: 500; background-color: #1e1e24; letter-spacing: 1.5px;"></div>
            </div>

            <div class="mb-4 conceptual-breakdown px-2">
                <h3 class="h6 text-body-secondary text-uppercase small fw-bold mb-2">
                    <i class="bi bi-file-earmark-text me-2 text-info"></i>Analysis
                </h3>
                <div class="text-body-emphasis reaction-explanation" style="text-align: justify; text-justify: inter-word;"></div>
            </div>

            <div class="alert alert-warning bg-warning-subtle border-warning border-start border-5 shadow-sm p-3 safety-matrix-block rounded-end">
                <h3 class="h6 text-uppercase small fw-bold mb-2 safety-heading">
                    <i class="bi bi-exclamation-triangle-fill me-2 text-warning"></i>Safety rules
                </h3>
                <ul class="list-unstyled mb-0 small fw-medium safety-list"></ul>
            </div>

            <aside class="reaction-feedback" aria-labelledby="reaction-feedback-title">
                <p class="reaction-feedback-label">Optional feedback</p>
                <h3 class="reaction-feedback-title" id="reaction-feedback-title">Help us understand your goal</h3>
                <a class="reaction-feedback-link" href="#" aria-label="Answer two quick questions by email">
                    Answer two quick questions
                    <i class="bi bi-arrow-up-right" aria-hidden="true"></i>
                </a>
                <p class="reaction-feedback-note">Opens your email app. No lab details are added.</p>
            </aside>

        </div>
    `;
    const equation = panel.querySelector('.reaction-equation');
    const explanation = panel.querySelector('.reaction-explanation');
    const safetyList = panel.querySelector('.safety-list');
    const feedbackLink = panel.querySelector('.reaction-feedback-link');
    if (!equation || !explanation || !safetyList || !feedbackLink)
        return;
    equation.textContent = reaction.equation;
    explanation.textContent = reaction.explanation;
    feedbackLink.href = buildFeedbackMailtoUrl();
    const safetyPoints = reaction.safety
        .split('|')
        .map(point => point.trim())
        .filter(point => point.length > 0);
    for (const point of safetyPoints.length > 0 ? safetyPoints : [reaction.safety]) {
        const item = document.createElement('li');
        item.className = 'mb-2';
        const icon = document.createElement('i');
        icon.className = 'bi bi-shield-exclamation me-2';
        icon.setAttribute('aria-hidden', 'true');
        item.append(icon, document.createTextNode(point));
        safetyList.append(item);
    }
}
function renderStatusMessage(panel, title, message, kind) {
    panel.innerHTML = kind === 'info'
        ? `
            <div class="alert alert-info bg-info-subtle text-info-emphasis border-info border-start border-5 shadow-sm p-3 rounded-end" role="status">
                <h3 class="h6 fw-bold mb-2"></h3>
                <p class="mb-0"></p>
            </div>
        `
        : '<div class="alert alert-danger bg-danger-subtle text-danger-emphasis border-danger" role="alert"></div>';
    if (kind === 'info') {
        const heading = panel.querySelector('h3');
        const body = panel.querySelector('p');
        if (heading)
            heading.textContent = title;
        if (body)
            body.textContent = message;
        return;
    }
    const body = panel.querySelector('[role="alert"]');
    if (body)
        body.textContent = `${title}: ${message}`;
}
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
        localStorage.setItem(config.getLabStorageKey('savedChemicals'), JSON.stringify(updatedChemicals));
        localStorage.setItem(config.getLabStorageKey('savedLiquidColor'), color);
        const mixtureEl = document.getElementById('current-mixture');
        if (mixtureEl) {
            mixtureEl.innerText = updatedChemicals.join(' + ');
        }
    }
    closeAllPopovers();
}
export function resetLaboratory() {
    localStorage.removeItem(config.getLabStorageKey('savedChemicals'));
    localStorage.removeItem(config.getLabStorageKey('savedLiquidColor'));
    localStorage.removeItem(config.getLabStorageKey('savedReaction'));
    currentAnalysisRunId += 1;
    activeAnalysisController?.abort();
    activeAnalysisController = null;
    setAnalysisPending(false);
    cancelReactionEffects();
    config.updateLabState({
        selectedChemicals: [],
        targetLiquidVol: 0,
        currentLiquidVol: 0,
        liquidColor: '#3399ff',
        streamColor: '#ffffff',
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
    const panel = document.getElementById('ai-response-content');
    if (panel) {
        panel.innerHTML = DEFAULT_REACTION_INSTRUCTION;
    }
    drawVesselAndFluid();
}
function getCsrfToken() {
    const cookiePrefix = 'csrftoken=';
    const csrfCookie = document.cookie
        .split(';')
        .map(cookie => cookie.trim())
        .find(cookie => cookie.startsWith(cookiePrefix));
    return csrfCookie
        ? decodeURIComponent(csrfCookie.slice(cookiePrefix.length))
        : '';
}
export function fireAIAnalysis() {
    if (activeAnalysisController)
        return;
    const state = config.getLabState();
    if (state.selectedChemicals.length === 0) {
        alert("Laboratory apparatus matrix is currently empty!");
        return;
    }
    const panel = document.getElementById('ai-response-content');
    if (!panel)
        return;
    const requestController = new AbortController();
    activeAnalysisController = requestController;
    setAnalysisPending(true);
    const analysisRunId = ++currentAnalysisRunId;
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
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData,
        credentials: 'same-origin',
        signal: requestController.signal
    })
        .then(res => res.text())
        .then(rawText => {
        if (analysisRunId !== currentAnalysisRunId)
            return;
        const cleanedText = rawText.replace(/[\n\r\t]/g, ' ');
        const resData = JSON.parse(cleanedText);
        if (resData.status === 'rate_limited') {
            capture('reaction_analysis_failed', {
                stage: 'rate_limited',
                duration_ms: Math.round(performance.now() - analysisStartedAt)
            });
            renderStatusMessage(panel, 'Please wait before trying again', resData.message || 'This network has reached its reaction analysis limit.', 'info');
        }
        else if (resData.status === 'insufficient_input') {
            capture('reaction_analysis_failed', {
                stage: 'insufficient_input',
                duration_ms: Math.round(performance.now() - analysisStartedAt)
            });
            localStorage.removeItem(config.getLabStorageKey('savedReaction'));
            renderStatusMessage(panel, 'Try a different setup', resData.message || 'Add another selected chemical and try again.', 'info');
        }
        else if (resData.status === 'success' && resData.data) {
            capture('reaction_analysis_completed', {
                chemical_count: state.selectedChemicals.length,
                vessel: state.currentVessel,
                effect: resData.data.effect,
                duration_ms: Math.round(performance.now() - analysisStartedAt)
            });
            localStorage.setItem(config.getLabStorageKey('savedReaction'), JSON.stringify(resData.data));
            const reaction = resData.data;
            renderReactionResult(panel, reaction);
            config.updateLabState({ isBubbling: false });
            if (reaction.effect === 'explosion') {
                triggerThermalBlast();
            }
            else if (reaction.effect === 'smoke') {
                triggerSmokeEffect();
            }
            else if (reaction.effect === 'color_change' && reaction.new_color !== 'none') {
                config.updateLabState({ liquidColor: reaction.new_color });
                localStorage.setItem(config.getLabStorageKey('savedLiquidColor'), reaction.new_color);
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
            renderStatusMessage(panel, 'Processing Fault', resData.message || 'The reaction response could not be displayed.', 'danger');
        }
    })
        .catch(err => {
        if (requestController.signal.aborted || analysisRunId !== currentAnalysisRunId)
            return;
        capture('reaction_analysis_failed', {
            stage: 'network_or_parse',
            duration_ms: Math.round(performance.now() - analysisStartedAt)
        });
        renderStatusMessage(panel, 'Network Runtime Error', err instanceof Error ? err.message : 'The reaction request failed.', 'danger');
    })
        .finally(() => {
        if (analysisRunId !== currentAnalysisRunId)
            return;
        activeAnalysisController = null;
        setAnalysisPending(false);
    });
}
document.addEventListener("DOMContentLoaded", () => {
    const reactionDemo = config.getReactionDemoConfig();
    const chemicalsStorageKey = config.getLabStorageKey('savedChemicals');
    const liquidColorStorageKey = config.getLabStorageKey('savedLiquidColor');
    const reactionStorageKey = config.getLabStorageKey('savedReaction');
    const savedChemicals = localStorage.getItem(chemicalsStorageKey);
    const savedLiquidColor = localStorage.getItem(liquidColorStorageKey);
    const preparedChemicals = savedChemicals
        ? JSON.parse(savedChemicals)
        : reactionDemo?.selectedChemicals || [];
    if (!savedChemicals && reactionDemo) {
        localStorage.setItem(chemicalsStorageKey, JSON.stringify(reactionDemo.selectedChemicals));
        localStorage.setItem(liquidColorStorageKey, reactionDemo.liquidColor);
    }
    if (preparedChemicals.length > 0) {
        config.updateLabState({
            selectedChemicals: preparedChemicals,
            currentVessel: reactionDemo?.vessel || config.getLabState().currentVessel
        });
        const mixtureEl = document.getElementById('current-mixture');
        if (mixtureEl) {
            mixtureEl.innerText = preparedChemicals.join(' + ');
        }
        const vol = Math.min(preparedChemicals.length * 30, 210);
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
    const preparedLiquidColor = savedLiquidColor || reactionDemo?.liquidColor;
    if (preparedLiquidColor) {
        config.updateLabState({ liquidColor: preparedLiquidColor });
    }
    if (preparedChemicals.length > 0 || preparedLiquidColor) {
        drawVesselAndFluid();
    }
    const savedData = localStorage.getItem(reactionStorageKey);
    if (savedData) {
        try {
            const reaction = JSON.parse(savedData);
            const panel = document.getElementById('ai-response-content');
            if (!panel)
                return;
            renderReactionResult(panel, reaction);
        }
        catch (e) {
            localStorage.removeItem(reactionStorageKey);
        }
    }
    else {
        const panel = document.getElementById('ai-response-content');
        if (panel) {
            panel.innerHTML = reactionDemo && preparedChemicals.length > 0
                ? DEMO_REACTION_INSTRUCTION
                : DEFAULT_REACTION_INSTRUCTION;
        }
    }
});
//# sourceMappingURL=interactions.js.map
