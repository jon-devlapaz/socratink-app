// js/store.js

const STORE_KEY = 'learnops_concepts';
const ACTIVE_KEY = 'learnops_active';

// Transient content store — full text, NOT in localStorage. Keyed by concept ID.
export const contentStore = new Map();

export function generateId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

export function loadConcepts() {
  try { 
    let arr = JSON.parse(localStorage.getItem(STORE_KEY)) || []; 
    // Migration: fix any concepts saved with invalid 'mapped' state during Library testing
    arr = arr.map(c => {
      if (c.state === 'mapped') c.state = 'growing';
      return c;
    });
    return arr;
  }
  catch { return []; }
}

export function saveConcepts(arr) {
  localStorage.setItem(STORE_KEY, JSON.stringify(arr));
}

export function getActiveId() {
  return localStorage.getItem(ACTIVE_KEY) || null;
}

export function setActiveId(id) {
  if (id) {
    localStorage.setItem(ACTIVE_KEY, id);
  } else {
    localStorage.removeItem(ACTIVE_KEY);
  }
}

export function getActiveConcept() {
  const id = getActiveId();
  if (!id) return null;
  return loadConcepts().find(c => c.id === id) || null;
}

export function getActiveTileIdx() {
  const id = getActiveId();
  if (!id) return -1;
  return loadConcepts().findIndex(c => c.id === id);
}

export function updateActiveConcept(patch) {
  const concepts = loadConcepts();
  const id = getActiveId();
  const idx = concepts.findIndex(c => c.id === id);
  if (idx === -1) return;
  Object.assign(concepts[idx], patch);
  saveConcepts(concepts);
}

export const STATES = {
  instantiated: { title:'', desc:'' },
  growing:      { title:'', desc:'' },
  fractured:    { title:'Misconception Detected', desc:'Knowledge gap found. Drill again to repair.' },
  hibernating:  { title:'Consolidating…',         desc:'Synaptic lockout enforced. Return tomorrow.' },
  actualized:   { title:'Consolidated',           desc:'Converted into durable understanding.' },
};
