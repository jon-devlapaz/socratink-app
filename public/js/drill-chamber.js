/* drill-chamber.js — production view module for the ironclad drill chamber.
   Design-of-record: public/_lab/drill-chamber-iterations.html?variant=ironclad
   Companion notes: public/_lab/drill-chamber-iterations.NOTES.md

   Public surface:
     - DrillChamber.show({conceptName, entryName, question})
     - DrillChamber.hide()
     - DrillChamber.appendHistoryTurn(role, text)   // role = 'ai' | 'learner'
     - DrillChamber.swapQuestion(text)               // animates the question swap
     - DrillChamber.setComposerEnabled(bool)
     - DrillChamber.getComposerValue()
     - DrillChamber.clearComposer()
     - DrillChamber.onSend(handler)                  // handler receives raw composer text
     - DrillChamber.onExit(handler)
*/

const els = {};
let sendHandler = null;
let exitHandler = null;
let historyTurns = 0;

function bind() {
  if (els.bound) return;
  els.view = document.getElementById('drill-chamber-view');
  els.conceptName = document.getElementById('chamber-concept-name');
  els.entryName = document.getElementById('chamber-entry-name');
  els.question = document.getElementById('chamber-question');
  els.active = document.getElementById('chamber-active');
  els.composer = document.getElementById('chamber-composer');
  els.send = document.getElementById('chamber-send');
  els.exit = document.getElementById('chamber-exit');
  els.historyWidget = document.getElementById('chamber-history-widget');
  els.historyCount = document.getElementById('chamber-history-count');
  els.historyToggle = document.getElementById('chamber-history-toggle');
  els.historyExpanded = document.getElementById('chamber-history-expanded');

  if (!els.view) return;

  els.send.addEventListener('click', () => {
    if (typeof sendHandler !== 'function') return;
    sendHandler(getComposerValue());
  });
  els.composer.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      els.send.click();
    }
  });
  els.exit.addEventListener('click', () => {
    if (typeof exitHandler === 'function') exitHandler();
  });
  els.historyToggle.addEventListener('click', () => {
    const expanded = els.historyWidget.classList.toggle('is-expanded');
    els.historyToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    els.historyToggle.textContent = expanded ? 'hide' : 'show';
  });

  els.bound = true;
}

// Track which primary view we hid so we can restore it on exit.
let hiddenPrimaryView = null;

function show({ conceptName, entryName, question }) {
  bind();
  if (!els.view) return;
  // Hide whichever primary view is currently visible. The app uses a
  // `.visible` class to mark the active primary view (map / library /
  // settings / ignition). The chamber takes over the screen, so the
  // current primary view must drop its `.visible` class while we're
  // open. cancelDrill() restores it via showMapView().
  hiddenPrimaryView = document.querySelector('.primary-view.visible, #map-view.visible');
  if (hiddenPrimaryView) hiddenPrimaryView.classList.remove('visible');

  els.conceptName.textContent = conceptName || '—';
  els.entryName.textContent = entryName || '—';
  els.question.textContent = question || '—';
  els.composer.value = '';
  setComposerEnabled(true);
  resetHistory();
  els.view.hidden = false;
  document.body.classList.add('chamber-open');
  requestAnimationFrame(() => els.composer.focus());
}

function hide() {
  bind();
  if (!els.view) return;
  els.view.hidden = true;
  document.body.classList.remove('chamber-open');
  // Note: cancelDrill() restores the proper primary view via showMapView();
  // we do not re-add `.visible` here to avoid stale-state restores.
  hiddenPrimaryView = null;
}

function resetHistory() {
  bind();
  historyTurns = 0;
  els.historyCount.textContent = '0';
  els.historyExpanded.innerHTML = '';
  els.historyWidget.hidden = true;
  els.historyWidget.classList.remove('is-expanded');
  els.historyToggle.setAttribute('aria-expanded', 'false');
  els.historyToggle.textContent = 'show';
}

function appendHistoryTurn(role, text) {
  bind();
  const turn = document.createElement('div');
  turn.className = 'drill-chamber__history-turn' + (role === 'learner' ? ' drill-chamber__history-turn--learner' : '');
  const meta = document.createElement('div');
  meta.className = 'drill-chamber__history-turn-meta';
  meta.textContent = role === 'learner' ? 'you' : 'socratink';
  const body = document.createElement('div');
  body.className = 'drill-chamber__history-body';
  body.textContent = text;
  turn.appendChild(meta);
  turn.appendChild(body);
  els.historyExpanded.appendChild(turn);
  historyTurns += 1;
  els.historyCount.textContent = String(historyTurns);
  els.historyWidget.hidden = false;
}

function swapQuestion(nextText) {
  bind();
  els.active.classList.add('is-fading-out');
  setTimeout(() => {
    els.question.textContent = nextText;
    els.composer.value = '';
    els.active.classList.remove('is-fading-out');
    void els.active.offsetWidth;
    els.active.classList.add('is-fading-in');
    setTimeout(() => els.active.classList.remove('is-fading-in'), 360);
    els.composer.focus();
  }, 240);
}

function setComposerEnabled(enabled) {
  bind();
  els.composer.disabled = !enabled;
  els.send.disabled = !enabled;
}

// Original placeholder, captured once so setLoading(false) can restore it.
const _originalPlaceholder = 'Write what comes to mind. Fragments are fine.';

/**
 * Toggle a "preparing the prompt" state on the composer. Used while
 * waiting for the AI's first turn after the chamber opens (5-10s
 * Gemini latency). NOT a chat-typing indicator -- this is page-load
 * state, not mid-conversation theatre.
 *
 * Sets the composer placeholder to a status string and disables input.
 * Adds data-loading on the active block for any optional CSS hooks.
 */
function setLoading(loading) {
  bind();
  if (!els.composer) return;
  if (loading) {
    els.composer.placeholder = 'Preparing your first question';
    els.active?.setAttribute('data-loading', 'true');
    setComposerEnabled(false);
  } else {
    els.composer.placeholder = _originalPlaceholder;
    els.active?.removeAttribute('data-loading');
  }
}

function getComposerValue() {
  bind();
  return (els.composer.value || '').trim();
}

function clearComposer() {
  bind();
  els.composer.value = '';
}

function onSend(handler) { sendHandler = handler; }
function onExit(handler) { exitHandler = handler; }

window.DrillChamber = {
  show, hide, appendHistoryTurn, swapQuestion,
  setComposerEnabled, setLoading,
  getComposerValue, clearComposer,
  onSend, onExit,
};
