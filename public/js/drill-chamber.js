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

const REQUIRED_ELEMENT_KEYS = [
  'view',
  'conceptName',
  'entryName',
  'question',
  'active',
  'composer',
  'send',
  'exit',
  'chatLog',
];

function hasRequiredElements() {
  return REQUIRED_ELEMENT_KEYS.every((key) => Boolean(els[key]));
}

function bind() {
  const view = document.getElementById('drill-chamber-view');
  if (els.bound && els.view === view) return hasRequiredElements();
  els.bound = false;
  els.view = view;
  els.conceptName = document.getElementById('chamber-concept-name');
  els.entryName = document.getElementById('chamber-entry-name');
  els.question = document.getElementById('chamber-question');
  els.active = document.getElementById('chamber-active');
  els.composer = document.getElementById('chamber-composer');
  els.send = document.getElementById('chamber-send');
  els.exit = document.getElementById('chamber-exit');
  els.chatLog = document.getElementById('chamber-chat-log');

  if (!hasRequiredElements()) return false;

  els.send.addEventListener('click', () => {
    if (!hasRequiredElements()) return;
    if (typeof sendHandler !== 'function') return;
    if (els.send.disabled) return;        // hard guard against spam
    // Validate BEFORE locking the UI. Without this, an empty-composer
    // click locks the composer and the upstream onSend handler returns
    // early on empty text, leaving the UI permanently disabled until
    // reload. Empty input is a no-op, no state change.
    const text = getComposerValue();
    if (!text) return;
    els.send.disabled = true;             // visually + functionally lock immediately
    els.composer.disabled = true;
    sendHandler(text);
  });
  els.composer.addEventListener('keydown', (e) => {
    if (!hasRequiredElements()) return;
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      els.send.click();
    }
  });
  els.exit.addEventListener('click', () => {
    if (!hasRequiredElements()) return;
    if (typeof exitHandler === 'function') exitHandler();
  });

  els.bound = true;
  return true;
}

function show({ conceptName, entryName, question }) {
  if (!bind()) return;
  els.active.querySelectorAll('.drill-chamber__creed').forEach((el) => el.remove());
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
  if (!bind()) return;
  els.view.hidden = true;
  document.body.classList.remove('chamber-open');
}

function resetHistory() {
  if (!bind()) return;
  historyTurns = 0;
  els.chatLog.innerHTML = '';
  els.chatLog.hidden = true;
}

function appendHistoryTurn(role, text) {
  if (!bind()) return;
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
  els.chatLog.appendChild(turn);
  historyTurns += 1;
  els.chatLog.hidden = false;
  els.view.scrollIntoView({ block: 'end', behavior: 'smooth' });
}

function swapQuestion(nextText) {
  if (!bind()) return;
  els.active.classList.add('is-fading-out');
  setTimeout(() => {
    if (!hasRequiredElements()) return;
    els.question.textContent = nextText;
    els.composer.value = '';
    els.active.classList.remove('is-fading-out');
    void els.active.offsetWidth;
    els.active.classList.add('is-fading-in');
    setTimeout(() => {
      els.active.classList.remove('is-fading-in');
      els.view?.scrollIntoView({ block: 'end', behavior: 'smooth' });
    }, 360);
    els.composer.focus();
  }, 240);
}

function setComposerEnabled(enabled) {
  if (!bind()) return;
  els.composer.disabled = !enabled;
  els.send.disabled = !enabled;
}

// Original placeholder, captured once so setLoading(false) can restore it.
const _originalPlaceholder = 'Write your reconstruction here. Fragments are fine.';

/**
 * Toggle a quiet pending state without taking the writing surface away.
 * The node prompt is already the first question, so loading must never
 * prevent the learner from starting their reconstruction.
 */
function setLoading(loading) {
  if (!bind()) return;
  if (loading) {
    els.composer.placeholder = _originalPlaceholder;
    els.active?.setAttribute('data-loading', 'true');
  } else {
    els.composer.placeholder = _originalPlaceholder;
    els.active?.removeAttribute('data-loading');
  }
}

function getComposerValue() {
  if (!bind()) return '';
  return (els.composer.value || '').trim();
}

function clearComposer() {
  if (!bind()) return;
  els.composer.value = '';
}

/**
 * Show the doctrinal first-cold-attempt creed in the chamber after
 * generative_commitment === true. Three lines, diamond bullets,
 * appended below the active question. Composer stays disabled --
 * the creed is a completion beat, not a prompt for more input.
 */
function appendCreed() {
  if (!bind()) return;
  const creedHtml = `
    <ul class="drill-chamber__creed">
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>You tried first.</strong> The entry stayed quiet until your guess existed.</span></li>
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>Study has a target now.</strong> Repair the gap this entry exposed.</span></li>
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>Return later.</strong> Only spaced re-drill can change the record.</span></li>
    </ul>
  `;
  els.question.insertAdjacentHTML('afterend', creedHtml);
  setComposerEnabled(false);
}

function onSend(handler) { sendHandler = handler; }
function onExit(handler) { exitHandler = handler; }

window.DrillChamber = {
  show, hide, appendHistoryTurn, swapQuestion,
  setComposerEnabled, setLoading,
  getComposerValue, clearComposer,
  appendCreed,
  onSend, onExit,
};
