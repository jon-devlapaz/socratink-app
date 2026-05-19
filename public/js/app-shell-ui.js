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
  const safeState = escHtml(String(concept?.state ?? ''));
  const safeId = escHtml(String(concept?.id ?? ''));
  const safeName = escHtml(concept.name);
  return `
        <div class="concept-dot" data-state="${safeState}"></div>
        <span class="concept-item-name">${safeName}</span>
        <button class="concept-actions" type="button" data-concept-id="${safeId}" onclick="App.toggleConceptActions(this)" aria-label="Concept actions for ${safeName}" aria-haspopup="menu" aria-expanded="false" title="Concept actions">
          <span class="material-symbols-outlined" aria-hidden="true">more_vert</span>
        </button>
        <div class="concept-action-menu" role="menu" hidden>
          <button class="concept-delete concept-action-menu-item" type="button" role="menuitem" data-concept-id="${safeId}" onclick="App.deleteConcept(this.dataset.conceptId,this)" aria-label="Delete concept ${safeName}">
            <span class="material-symbols-outlined" aria-hidden="true">delete</span>
            <span>Delete concept</span>
          </button>
        </div>`;
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
    item.dataset.conceptId = String(concept?.id ?? '');
    item.innerHTML = conceptListItemHtml(concept);
    item.addEventListener('click', e => {
      if (elementCtor && e.target instanceof elementCtor && e.target.closest('.concept-actions, .concept-action-menu')) return;
      onOpenConcept(concept);
    });
    conceptListEl.appendChild(item);
  });
}
