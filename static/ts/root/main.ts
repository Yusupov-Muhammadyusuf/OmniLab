import * as config from '../configuration/config.js';
import * as ui from '../userInterface/ui.js';
import * as render from '../rendering/render.js';
import * as interactions from '../interactions/interactions.js';
import { capture } from '../analytics/analytics.js';

declare global {
    interface Window {
        chemicalDataUrl?: string;
        toggleCustomPopover: typeof ui.toggleCustomPopover;
        selectVessel: typeof ui.selectVessel;
        toggleTheme: typeof ui.toggleTheme;
        resetLaboratory: typeof interactions.resetLaboratory;
        fireAIAnalysis: typeof interactions.fireAIAnalysis;
        allowDrop: typeof interactions.allowDrop;
        drop: typeof interactions.drop;
    }
}

document.addEventListener("DOMContentLoaded", function(): void {
    capture('lab_viewed', { route: window.location.pathname });
    const reactionDemo = config.getReactionDemoConfig();
    if (reactionDemo) {
        const visitSource = config.getVisitSource();
        capture('reaction_demo_entered', {
            demo_version: reactionDemo.version,
            chemical_count: reactionDemo.selectedChemicals.length,
            vessel: reactionDemo.vessel,
            ...(visitSource ? { visit_source: visitSource } : {})
        });
    }
    ui.resizeCanvas();
    requestAnimationFrame(engineLoop);
    interactions.setupCanvasDrag();
    ui.setupSearchFunction();

    const burnerOpt = document.getElementById('opt-burner');
    if (burnerOpt) {
        burnerOpt.addEventListener('click', () => {
            ui.selectVessel('burner');
            config.updateLabState({ burnerActive: true });
        });
    }

    const jsonUrl: string = window.chemicalDataUrl || "/static/js/chemicaldata.json";

    fetch(jsonUrl) 
        .then((response: Response) => {
            if (!response.ok) throw new Error("File Not Found! Status: " + response.status);
            return response.json();
        })
        .then((data: any) => {
            config.updateLabState({ chemicalDatabase: data });
            ui.buildChemicalMenu();
        })
        .catch((error: any) => console.error("Error loading json:", error));

    if (config.canvas) {
        config.canvas.addEventListener('dragover', interactions.allowDrop as EventListener);
        config.canvas.addEventListener('drop', interactions.drop as EventListener);
    }

    const chemBtn = document.getElementById('trigger-chemicals');
    const appBtn = document.getElementById('trigger-apparatus');
    const themeBtn = document.getElementById('trigger-theme');
    const resetBtn = document.getElementById('btn-reset-lab');
    const analyzeBtn = document.getElementById('btn-fire-analysis');

    if (chemBtn) chemBtn.addEventListener('click', (e: MouseEvent) => ui.toggleCustomPopover(e, 'chemicals'));
    if (appBtn) appBtn.addEventListener('click', (e: MouseEvent) => ui.toggleCustomPopover(e, 'apparatus'));
    if (themeBtn) themeBtn.addEventListener('click', ui.toggleTheme);
    if (resetBtn) resetBtn.addEventListener('click', interactions.resetLaboratory);
    if (analyzeBtn) analyzeBtn.addEventListener('click', interactions.fireAIAnalysis);

    const beakerOpt = document.getElementById('opt-beaker');
    const tubeOpt = document.getElementById('opt-tube');
    const flaskOpt = document.getElementById('opt-flask');

    if (beakerOpt) beakerOpt.addEventListener('click', () => ui.selectVessel('beaker'));
    if (tubeOpt) tubeOpt.addEventListener('click', () => ui.selectVessel('tube'));
    if (flaskOpt) flaskOpt.addEventListener('click', () => ui.selectVessel('flask'));

    document.addEventListener('click', ui.closeAllPopovers);
    window.addEventListener('resize', ui.resizeCanvas);
});

function engineLoop(): void {
    const state = config.getLabState();
    
    if (state.currentLiquidVol < state.targetLiquidVol) {
        config.updateLabState({
            currentLiquidVol: state.currentLiquidVol + 2.0,
            waveTime: state.waveTime + 0.25
        });
    } else {
        config.updateLabState({ streamActive: false });
        if (state.currentLiquidVol > 0) {
            config.updateLabState({ waveTime: state.waveTime + 0.06 });
        }
    }
    render.drawVesselAndFluid();
    requestAnimationFrame(engineLoop);
}

window.toggleCustomPopover = ui.toggleCustomPopover;
window.selectVessel = ui.selectVessel;
window.toggleTheme = ui.toggleTheme;
window.resetLaboratory = interactions.resetLaboratory;
window.fireAIAnalysis = interactions.fireAIAnalysis;
window.allowDrop = interactions.allowDrop;
window.drop = interactions.drop;
