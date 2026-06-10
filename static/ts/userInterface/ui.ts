import * as config from '../configuration/config.js';

export function buildChemicalMenu(): void {
    const container = document.getElementById('chem-matrix-target');
    if(!container) return;
    container.innerHTML = '';
    
    const state = config.getLabState();
    
    state.chemicalDatabase.forEach(chem => {
        const card = document.createElement('div');
        card.className = 'chemical-card';
        card.setAttribute('draggable', 'true');
        card.setAttribute('id', `chem-item-${chem.id}`);
        card.setAttribute('data-name', chem.id);
        card.setAttribute('data-color', chem.color);
        card.style.borderColor = chem.color;
        card.addEventListener('dragstart', (ev: DragEvent) => {
            if (ev.dataTransfer && ev.target) {
                ev.dataTransfer.setData("text", (ev.target as HTMLElement).id);
            }
        });
        
        card.innerHTML = `
            <span class="chemical-symbol" style="color:${chem.color}">${chem.id}</span>
            <span class="chemical-name" style="color:var(--text-color)">${chem.name}</span>
        `;
        container.appendChild(card);
    });
}

export function setupSearchFunction(): void {
    const searchInput = document.getElementById('chem-search-input') as HTMLInputElement | null;
    if (!searchInput) return;

    searchInput.addEventListener('keyup', function(this: HTMLInputElement) {
        const value = this.value.toLowerCase().trim();
        const cards = document.querySelectorAll('.chemical-card');

        cards.forEach(cardNode => {
            const card = cardNode as HTMLElement;
            const id = card.getAttribute('data-name') ? card.getAttribute('data-name')!.toLowerCase() : '';
            const fullName = card.textContent ? card.textContent.toLowerCase() : '';

            if (id.includes(value) || fullName.includes(value)) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    });

    searchInput.addEventListener('click', function(e: MouseEvent) {
        e.stopPropagation();
    });
}

export function toggleCustomPopover(event: MouseEvent, panelId: string): void {
    event.stopPropagation();
    const target = document.getElementById(`sub-panel-${panelId}`);
    const trigger = document.getElementById(`trigger-${panelId}`);
    if (!target || !trigger) return;
    
    const isAlreadyOpen = target.style.display === 'block';
    
    closeAllPopovers();

    if (!isAlreadyOpen) {
        target.style.display = 'block';
        trigger.classList.add('active');
        if(panelId === 'chemicals') {
            setTimeout(() => { 
                const input = document.getElementById('chem-search-input') as HTMLInputElement | null;
                if (input) input.focus(); 
            }, 50);
        }
    }
}

export function closeAllPopovers(): void {
    document.querySelectorAll('.floating-popover-panel').forEach(p => {
        (p as HTMLElement).style.display = 'none';
    });
    document.querySelectorAll('.toolbar-trigger-btn').forEach(b => {
        (b as HTMLElement).classList.remove('active');
    });
}

export function selectVessel(type: 'flask' | 'beaker' | 'tube' | 'burner'): void {
    const state = config.getLabState();
    
    if (type === 'burner') {
        const isActive = !state.burnerActive;
        config.updateLabState({ burnerActive: isActive });
        
        const burnerCard = document.getElementById('opt-burner');
        if (burnerCard) {
            if (isActive) burnerCard.classList.add('selected');
            else burnerCard.classList.remove('selected');
        }
    } else {
        config.updateLabState({ currentVessel: type });
        document.querySelectorAll('.apparatus-option-card').forEach(c => {
            if (c.id !== 'opt-burner') (c as HTMLElement).classList.remove('selected');
        });
        const targetCard = document.getElementById(`opt-${type}`);
        if (targetCard) targetCard.classList.add('selected');
    }
    closeAllPopovers();
}

export function toggleTheme(): void {
    const html = document.documentElement;
    const newTheme = html.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
    html.setAttribute('data-theme', newTheme);
    config.updateLabState({ theme: newTheme });
    closeAllPopovers();
}

export function resizeCanvas(): void {
    if(!config.canvas || !config.canvas.parentElement) return;
    config.canvas.width = config.canvas.parentElement.clientWidth;
    config.canvas.height = config.canvas.parentElement.clientHeight;
}