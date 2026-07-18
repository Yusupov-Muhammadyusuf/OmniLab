import * as config from '../configuration/config.js';
import { captureLabSetupStarted } from '../analytics/analytics.js';
export function buildChemicalMenu(onSelectChemical) {
    const container = document.getElementById('chem-matrix-target');
    if (!container)
        return;
    container.innerHTML = '';
    const state = config.getLabState();
    state.chemicalDatabase.forEach(chem => {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'chemical-card';
        card.setAttribute('draggable', 'true');
        card.setAttribute('id', `chem-item-${chem.id}`);
        card.setAttribute('data-name', chem.id);
        card.setAttribute('data-color', chem.color);
        card.setAttribute('aria-label', `Add ${chem.name} (${chem.id}) to the lab`);
        card.setAttribute('aria-pressed', state.selectedChemicals.includes(chem.id) ? 'true' : 'false');
        card.style.borderColor = chem.color;
        card.addEventListener('dragstart', (ev) => {
            if (ev.dataTransfer && ev.currentTarget) {
                ev.dataTransfer.setData("text", ev.currentTarget.id);
            }
        });
        card.addEventListener('click', (ev) => {
            ev.stopPropagation();
            onSelectChemical(chem.id, chem.color);
        });
        card.innerHTML = `
            <span class="chemical-symbol" style="color:${chem.color}">${chem.id}</span>
            <span class="chemical-name" style="color:var(--text-color)">${chem.name}</span>
        `;
        container.appendChild(card);
    });
}
export function setupSearchFunction() {
    const searchInput = document.getElementById('chem-search-input');
    if (!searchInput)
        return;
    searchInput.addEventListener('keyup', function () {
        const value = this.value.toLowerCase().trim();
        const cards = document.querySelectorAll('.chemical-card');
        cards.forEach(cardNode => {
            const card = cardNode;
            const id = card.getAttribute('data-name') ? card.getAttribute('data-name').toLowerCase() : '';
            const fullName = card.textContent ? card.textContent.toLowerCase() : '';
            if (id.includes(value) || fullName.includes(value)) {
                card.style.display = 'block';
            }
            else {
                card.style.display = 'none';
            }
        });
    });
    searchInput.addEventListener('click', function (e) {
        e.stopPropagation();
    });
}
export function toggleCustomPopover(event, panelId) {
    event.stopPropagation();
    const target = document.getElementById(`sub-panel-${panelId}`);
    const trigger = document.getElementById(`trigger-${panelId}`);
    if (!target || !trigger)
        return;
    const isAlreadyOpen = target.style.display === 'block';
    closeAllPopovers();
    if (!isAlreadyOpen) {
        target.style.display = 'block';
        trigger.classList.add('active');
        trigger.setAttribute('aria-expanded', 'true');
        if (panelId === 'chemicals') {
            setTimeout(() => {
                const input = document.getElementById('chem-search-input');
                if (input)
                    input.focus();
            }, 50);
        }
        else if (panelId === 'apparatus') {
            setTimeout(() => {
                const option = target.querySelector('.apparatus-option-card.selected, .apparatus-option-card');
                option?.focus();
            }, 50);
        }
    }
}
export function closeAllPopovers() {
    document.querySelectorAll('.floating-popover-panel').forEach(p => {
        p.style.display = 'none';
    });
    document.querySelectorAll('.toolbar-trigger-btn').forEach(b => {
        b.classList.remove('active');
        b.setAttribute('aria-expanded', 'false');
    });
}
export function selectVessel(type) {
    const state = config.getLabState();
    if (type === 'burner') {
        const isActive = !state.burnerActive;
        config.updateLabState({ burnerActive: isActive });
        const burnerCard = document.getElementById('opt-burner');
        if (burnerCard) {
            burnerCard.classList.toggle('selected', isActive);
            burnerCard.setAttribute('aria-pressed', isActive ? 'true' : 'false');
        }
    }
    else {
        config.updateLabState({ currentVessel: type });
        document.querySelectorAll('.apparatus-option-card').forEach(c => {
            if (c.id !== 'opt-burner') {
                c.classList.remove('selected');
                c.setAttribute('aria-pressed', 'false');
            }
        });
        const targetCard = document.getElementById(`opt-${type}`);
        if (targetCard) {
            targetCard.classList.add('selected');
            targetCard.setAttribute('aria-pressed', 'true');
        }
    }
    const updatedState = config.getLabState();
    captureLabSetupStarted({
        vessel: updatedState.currentVessel,
        burner_active: updatedState.burnerActive
    });
    closeAllPopovers();
}
export function toggleTheme() {
    const html = document.documentElement;
    const newTheme = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    config.updateLabState({ theme: newTheme });
    closeAllPopovers();
}
export function resizeCanvas() {
    if (!config.canvas || !config.canvas.parentElement)
        return;
    config.canvas.width = config.canvas.parentElement.clientWidth;
    config.canvas.height = config.canvas.parentElement.clientHeight;
}
//# sourceMappingURL=ui.js.map
