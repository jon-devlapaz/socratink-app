// js/store.js

const STORE_KEY = 'learnops_concepts';
const ACTIVE_KEY = 'learnops_active';
const CANONICAL_DRILL_PHASES = new Set(['cold_attempt', 'study', 're_drill']);
const LEGACY_NON_SOLID_STATUSES = new Set(['deep', 'shallow', 'misconception']);

// Transient content store — full text, NOT in localStorage. Keyed by concept ID.
export const contentStore = new Map();

export function generateId() {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

function normalizeDrillNode(targetObj) {
  if (!targetObj || typeof targetObj !== 'object') return false;

  let changed = false;
  const legacyStatus = targetObj.drill_status;

  if (typeof legacyStatus === 'undefined') {
    targetObj.drill_status = null;
    changed = true;
  } else if (legacyStatus === 'solid') {
    targetObj.drill_status = 'solidified';
    changed = true;
  } else if (LEGACY_NON_SOLID_STATUSES.has(legacyStatus)) {
    if (!targetObj.gap_type) {
      targetObj.gap_type = legacyStatus;
    }
    targetObj.drill_status = 'drilled';
    changed = true;
  }

  if (typeof targetObj.drill_phase === 'undefined') {
    targetObj.drill_phase = null;
    changed = true;
  } else if (targetObj.drill_phase !== null && !CANONICAL_DRILL_PHASES.has(targetObj.drill_phase)) {
    targetObj.drill_phase = null;
    changed = true;
  }

  if (typeof targetObj.cold_attempt_at === 'undefined') {
    targetObj.cold_attempt_at = null;
    changed = true;
  }
  if (typeof targetObj.study_completed_at === 'undefined') {
    targetObj.study_completed_at = null;
    changed = true;
  }
  if (typeof targetObj.re_drill_eligible_after === 'undefined') {
    targetObj.re_drill_eligible_after = null;
    changed = true;
  }
  if (typeof targetObj.re_drill_count !== 'number') {
    targetObj.re_drill_count = Number.isFinite(Number(targetObj.re_drill_count))
      ? Number(targetObj.re_drill_count)
      : 0;
    changed = true;
  }
  if (typeof targetObj.re_drill_band === 'undefined') {
    targetObj.re_drill_band = null;
    changed = true;
  }
  if (typeof targetObj.gap_type === 'undefined') {
    targetObj.gap_type = null;
    changed = true;
  }
  if (typeof targetObj.gap_description === 'undefined') {
    targetObj.gap_description = null;
    changed = true;
  }
  if (typeof targetObj.last_drilled === 'undefined') {
    targetObj.last_drilled = null;
    changed = true;
  }

  return changed;
}

export function normalizeGraphData(rawGraphData) {
  if (!rawGraphData) return { graphData: rawGraphData, changed: false };

  const graphData = typeof rawGraphData === 'string' ? JSON.parse(rawGraphData) : rawGraphData;
  let changed = false;

  if (graphData.metadata) {
    changed = normalizeDrillNode(graphData.metadata) || changed;
  }

  (graphData.backbone || []).forEach((item) => {
    changed = normalizeDrillNode(item) || changed;
  });

  (graphData.clusters || []).forEach((cluster) => {
    changed = normalizeDrillNode(cluster) || changed;
    (cluster.subnodes || []).forEach((subnode) => {
      changed = normalizeDrillNode(subnode) || changed;
    });
  });

  return { graphData, changed };
}

export function loadConcepts() {
  try {
    let arr = JSON.parse(localStorage.getItem(STORE_KEY)) || [];
    let changedAny = false;
    arr = arr.map(c => {
      if (c.state === 'mapped') c.state = 'growing';

      if (c.graphData) {
        try {
          const { graphData, changed } = normalizeGraphData(c.graphData);
          if (changed) {
            c.graphData = JSON.stringify(graphData);
            changedAny = true;
          }
        } catch (err) {}
      }

      return c;
    });
    if (changedAny) {
      saveConcepts(arr);
    }
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
  fractured:    { title:'Worth revisiting', desc:'The next repair path is visible.' },
  hibernating:  { title:'Spacing window',   desc:'Work another room before returning.' },
  actualized:   { title:'Ready for re-drill', desc:'Return with a spaced reconstruction.' },
};
