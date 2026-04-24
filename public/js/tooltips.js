import {
  computePosition, flip, shift, offset, arrow,
} from 'https://cdn.jsdelivr.net/npm/@floating-ui/dom@1.6.3/+esm';

const OPEN_DELAY = 300;
const CLOSE_DELAY = 150;

const copy = {};

const state = new Map();

function ensureRoot() {
  let root = document.getElementById('tooltip-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'tooltip-root';
    root.setAttribute('aria-hidden', 'true');
    document.body.appendChild(root);
  }
  return root;
}

function buildTooltip(id, trigger) {
  const root = ensureRoot();
  let el = document.getElementById(id);
  if (el && el.classList.contains('help-tip')) {
    return {
      el,
      arrowEl: el.querySelector('.help-tip__arrow'),
      closeEl: el.querySelector('.help-tip__close'),
    };
  }
  el = document.createElement('div');
  el.id = id;
  el.className = 'help-tip';
  el.setAttribute('role', 'tooltip');
  el.dataset.show = 'false';
  el.dataset.placement = 'top';
  el.textContent = copy[id] || '';
  const arrowEl = document.createElement('div');
  arrowEl.className = 'help-tip__arrow';
  el.appendChild(arrowEl);
  const closeEl = document.createElement('button');
  closeEl.type = 'button';
  closeEl.className = 'help-tip__close';
  closeEl.setAttribute('aria-label', 'Close');
  closeEl.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">close</span>';
  closeEl.addEventListener('click', (e) => {
    e.stopPropagation();
    const owner = el._trigger;
    if (owner) hardClose(owner, { restoreFocus: true });
  });
  el.appendChild(closeEl);
  el._trigger = trigger;
  root.appendChild(el);
  return { el, arrowEl, closeEl };
}

function getState(trigger) {
  let s = state.get(trigger);
  if (s) return s;
  const id = trigger.dataset.tooltipId || trigger.getAttribute('aria-describedby');
  if (!id) return null;
  const { el, arrowEl, closeEl } = buildTooltip(id, trigger);
  el._trigger = trigger;
  s = {
    tooltip: el,
    arrowEl,
    closeEl,
    openT: null,
    closeT: null,
    openedBy: null, // 'hover' | 'focus' | 'pin'
  };
  state.set(trigger, s);
  return s;
}

async function position(trigger, tooltip, arrowEl) {
  const result = await computePosition(trigger, tooltip, {
    placement: 'top',
    middleware: [
      offset(8),
      flip({ padding: 8 }),
      shift({ padding: 8 }),
      arrow({ element: arrowEl }),
    ],
  });
  Object.assign(tooltip.style, {
    left: `${result.x}px`,
    top: `${result.y}px`,
  });
  tooltip.dataset.placement = result.placement;
  const side = result.placement.split('-')[0];
  const opposite = { top: 'bottom', bottom: 'top', left: 'right', right: 'left' }[side];
  const arrowData = result.middlewareData.arrow || {};
  Object.assign(arrowEl.style, {
    left: arrowData.x != null ? `${arrowData.x}px` : '',
    top: arrowData.y != null ? `${arrowData.y}px` : '',
    right: '',
    bottom: '',
    [opposite]: '-5px',
  });
}

async function show(trigger, source) {
  const s = getState(trigger);
  if (!s) return;
  if (s.closeT) { clearTimeout(s.closeT); s.closeT = null; }
  if (s.openT) { clearTimeout(s.openT); s.openT = null; }
  try {
    await position(trigger, s.tooltip, s.arrowEl);
    s.tooltip.dataset.show = 'true';
    s.tooltip.dataset.pinned = source === 'pin' ? 'true' : 'false';
    s.openedBy = source;
    if (source === 'pin') {
      trigger.dataset.pinned = 'true';
    }
  } catch (err) {
    console.warn('[tooltips] position failed', err);
  }
}

function openSoon(trigger, source) {
  const s = getState(trigger);
  if (!s) return;
  if (s.closeT) { clearTimeout(s.closeT); s.closeT = null; }
  if (s.openT) return;
  if (s.openedBy === 'pin') return;
  if (s.tooltip.dataset.show === 'true') return;
  s.openT = setTimeout(() => {
    s.openT = null;
    show(trigger, source);
  }, OPEN_DELAY);
}

function closeSoon(trigger, source) {
  const s = state.get(trigger);
  if (!s) return;
  if (s.openedBy === 'pin') return;
  if (s.openedBy && s.openedBy !== source) return;
  if (s.openT) { clearTimeout(s.openT); s.openT = null; }
  if (s.closeT) return;
  s.closeT = setTimeout(() => {
    s.closeT = null;
    hardClose(trigger);
  }, CLOSE_DELAY);
}

function hardClose(trigger, opts = {}) {
  const s = state.get(trigger);
  if (!s) return;
  const wasPinned = s.openedBy === 'pin';
  if (s.openT) clearTimeout(s.openT);
  if (s.closeT) clearTimeout(s.closeT);
  s.openT = s.closeT = null;
  s.openedBy = null;
  s.tooltip.dataset.show = 'false';
  s.tooltip.dataset.pinned = 'false';
  delete trigger.dataset.pinned;
  if (wasPinned && opts.restoreFocus) {
    try { trigger.focus({ preventScroll: true }); } catch (_) { /* noop */ }
  }
}

function closeAll() {
  state.forEach((_, trigger) => hardClose(trigger));
}

function closeAllExcept(except) {
  state.forEach((_, trigger) => { if (trigger !== except) hardClose(trigger); });
}

function triggerFrom(ev) {
  const t = ev.target;
  if (!t || typeof t.closest !== 'function') return null;
  return t.closest('.js-tooltip-trigger');
}

document.addEventListener('mouseover', (e) => {
  const t = triggerFrom(e);
  if (!t) return;
  openSoon(t, 'hover');
});

document.addEventListener('mouseout', (e) => {
  const t = triggerFrom(e);
  if (!t) return;
  const to = e.relatedTarget;
  if (to && typeof to.closest === 'function') {
    if (t.contains(to)) return;
    if (to.closest('.js-tooltip-trigger') === t) return;
    const s = state.get(t);
    if (s && s.tooltip.contains(to)) return;
  }
  closeSoon(t, 'hover');
});

document.addEventListener('focusin', (e) => {
  const t = triggerFrom(e);
  if (!t) return;
  openSoon(t, 'focus');
});

document.addEventListener('focusout', (e) => {
  const t = triggerFrom(e);
  if (!t) return;
  closeSoon(t, 'focus');
});

document.addEventListener('click', (e) => {
  const t = triggerFrom(e);
  if (t) {
    e.preventDefault();
    const s = getState(t);
    if (!s) return;
    if (s.openedBy === 'pin') {
      hardClose(t);
    } else {
      closeAllExcept(t);
      show(t, 'pin');
    }
    return;
  }
  // Outside click — dismiss pinned
  state.forEach((s, trigger) => {
    if (s.openedBy !== 'pin') return;
    if (s.tooltip.contains(e.target)) return;
    hardClose(trigger);
  });
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    let restored = false;
    state.forEach((s, trigger) => {
      if (s.openedBy === 'pin' && !restored) {
        hardClose(trigger, { restoreFocus: true });
        restored = true;
      } else {
        hardClose(trigger);
      }
    });
  }
});

window.addEventListener('resize', closeAll);
window.addEventListener('scroll', (e) => {
  // Close on scroll only if the scroll is not inside a tooltip.
  state.forEach((s, trigger) => {
    if (s.tooltip.contains(e.target)) return;
    hardClose(trigger);
  });
}, { passive: true, capture: true });

function bindAll() {
  document.querySelectorAll('.js-tooltip-trigger').forEach((t) => { getState(t); });
}
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', bindAll);
} else {
  bindAll();
}

export const Tooltips = { closeAll, bindAll };
window.Tooltips = Tooltips;
