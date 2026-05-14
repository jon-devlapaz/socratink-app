import { escHtml } from './html.js';

export function openDrawer({ drawer, drawerToggle, documentRef = document }) {
  drawer.dataset.open = 'true';
  documentRef.body.dataset.drawerOpen = 'true';
  if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'true');
}

export function closeDrawer({ drawer, drawerToggle, documentRef = document }) {
  drawer.dataset.open = 'false';
  documentRef.body.dataset.drawerOpen = 'false';
  if (drawerToggle) drawerToggle.setAttribute('aria-expanded', 'false');
}

export function toggleDrawer({ drawer, drawerToggle, documentRef = document, audio }) {
  audio.playDrawerToggle();
  drawer.dataset.open === 'true'
    ? closeDrawer({ drawer, drawerToggle, documentRef })
    : openDrawer({ drawer, drawerToggle, documentRef });
}

export function clearSettingsPanel({ documentRef = document } = {}) {
  const host = documentRef.getElementById('sidebar-settings-host');
  const settingsPanel = host?.querySelector('.settings-panel');
  if (!settingsPanel) return;
  const settingsBtn = documentRef.getElementById('nav-settings');
  if (settingsBtn) delete settingsBtn.dataset.engaged;
  host.innerHTML = '';
}

export function conceptListItemHtml(concept) {
  return `
        <div class="concept-dot" data-state="${concept.state}"></div>
        <span class="concept-item-name">${escHtml(concept.name)}</span>
        <button class="concept-delete" onclick="App.deleteConcept('${concept.id}',this)" aria-label="Delete concept ${escHtml(concept.name)}" title="Delete concept">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>`;
}

export function renderConceptList({
  concepts,
  activeId,
  conceptListEl,
  documentRef = document,
  elementCtor = typeof Element !== 'undefined' ? Element : null,
  onOpenConcept,
}) {
  conceptListEl.innerHTML = '';

  concepts.forEach((concept) => {
    const item = documentRef.createElement('div');
    item.className = 'concept-item' + (concept.id === activeId ? ' active' : '');
    item.innerHTML = conceptListItemHtml(concept);
    item.addEventListener('click', e => {
      if (elementCtor && e.target instanceof elementCtor && e.target.closest('.concept-delete')) return;
      onOpenConcept(concept);
    });
    conceptListEl.appendChild(item);
  });
}
