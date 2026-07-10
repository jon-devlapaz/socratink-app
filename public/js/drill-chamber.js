/* drill-chamber.js — production view module for the ironclad drill chamber.
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
let completionHandler = null;
let historyTurns = 0;
let speechRecognition = null;
let listening = false;
let speechBaseText = '';
let tutorVoiceEnabled = false;
let lastSpokenQuestion = '';
let pendingVerdictTimer = null;
let pendingVerdictShown = false;
const DEFAULT_SEND_LABEL = 'Check my answer';
const DEFAULT_HINT = 'A sentence is enough.';
const EMPTY_REPLY_HINT = 'Write a sentence before checking.';
const CHECKING_REPLY_HINT = 'Checking your answer…';
const PENDING_VERDICT = 'Answer received • Checking the link you wrote.';
const PENDING_VERDICT_DELAY_MS = 1200;
const _originalPlaceholder = 'Write your reconstruction here. Fragments are fine.';
const MIC_INPUT_PREF_KEY = 'socratink.loop.micInput';
const TUTOR_VOICE_PREF_KEY = 'socratink.loop.tutorVoice';

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
  if (els.bound && els.view === view) {
    els.hint = document.getElementById('chamber-hint');
    els.verdict = document.getElementById('chamber-verdict');
    return hasRequiredElements();
  }
  els.bound = false;
  els.view = view;
  els.conceptName = document.getElementById('chamber-concept-name');
  els.entryName = document.getElementById('chamber-entry-name');
  els.question = document.getElementById('chamber-question');
  els.active = document.getElementById('chamber-active');
  els.composer = document.getElementById('chamber-composer');
  els.send = document.getElementById('chamber-send');
  els.mic = document.getElementById('chamber-mic');
  els.tutorVoice = document.getElementById('chamber-tutor-voice');
  els.voiceStatus = document.getElementById('chamber-voice-status');
  els.hint = document.getElementById('chamber-hint');
  els.exit = document.getElementById('chamber-exit');
  els.chatLog = document.getElementById('chamber-chat-log');
  els.verdict = document.getElementById('chamber-verdict');

  if (!hasRequiredElements()) return false;

  els.send.addEventListener('click', () => {
    if (!hasRequiredElements()) return;
    if (completionHandler) {
      completionHandler();
      return;
    }
    if (typeof sendHandler !== 'function') return;
    if (els.send.disabled) return;        // hard guard against spam
    // Validate BEFORE locking the UI. Without this, an empty-composer
    // click locks the composer and the upstream onSend handler returns
    // early on empty text, leaving the UI permanently disabled until
    // reload. Empty input is a no-op, no state change.
    const text = getComposerValue();
    if (!text) {
      setComposerHint(EMPTY_REPLY_HINT);
      els.composer.focus();
      return;
    }
    els.send.disabled = true;             // visually + functionally lock immediately
    els.composer.disabled = true;
    sendHandler(text);
  });
  els.composer.addEventListener('input', () => {
    if (getComposerValue()) resetComposerHint();
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
  initVoiceControls();

  els.bound = true;
  return true;
}

function show({ conceptName, entryName, question }) {
  if (!bind()) return;
  setLoading(false);
  els.active.querySelectorAll('.drill-chamber__creed').forEach((el) => el.remove());
  clearCompletionAction();
  clearVerdict();
  resetComposerHint();
  els.conceptName.textContent = conceptName || '—';
  els.entryName.textContent = entryName || '—';
  els.question.textContent = question || '—';
  els.composer.value = '';
  setComposerEnabled(true);
  syncVoiceControls();
  lastSpokenQuestion = '';
  speakTutorQuestion(question || '—');
  resetHistory();
  els.view.hidden = false;
  document.body.classList.add('chamber-open');
  requestAnimationFrame(() => {
    if (!hasRequiredElements() || !els.view.isConnected || !els.composer.isConnected) return;
    const active = document.activeElement;
    const canClaimFocus = !active
      || active === document.body
      || active === document.documentElement
      || els.view.contains(active);
    if (canClaimFocus) els.composer.focus();
  });
}

function hide() {
  if (!bind()) return;
  stopSpeech();
  setLoading(false);
  clearCompletionAction();
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
  meta.textContent = role === 'learner' ? 'Your answer' : 'Prompt';
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
  clearCompletionAction();
  clearVerdict();
  els.active.classList.add('is-fading-out');
  setTimeout(() => {
    if (!hasRequiredElements()) return;
    els.question.textContent = nextText;
    els.composer.value = '';
    speakTutorQuestion(nextText);
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
  if (!enabled && listening) speechRecognition?.stop();
  if (enabled) clearCompletionAction();
  els.composer.disabled = !enabled;
  els.send.disabled = !enabled;
  if (els.mic && !els.mic.hidden) els.mic.disabled = !enabled;
}

/**
 * Toggle a quiet pending state without taking the writing surface away.
 * The node prompt is already the first question, so loading must never
 * prevent the learner from starting their reconstruction.
 */
function setLoading(loading, { checkingAnswer = false } = {}) {
  if (!bind()) return;
  if (loading) {
    els.composer.placeholder = _originalPlaceholder;
    els.active?.setAttribute('data-loading', 'true');
    if (checkingAnswer) {
      if (els.hint) {
        els.hint.textContent = CHECKING_REPLY_HINT;
        els.hint.classList?.remove?.('is-error');
      }
      setVoiceStatus(CHECKING_REPLY_HINT);
      if (pendingVerdictTimer != null) clearTimeout(pendingVerdictTimer);
      pendingVerdictTimer = setTimeout(() => {
        pendingVerdictTimer = null;
        pendingVerdictShown = true;
        renderVerdict(PENDING_VERDICT);
      }, PENDING_VERDICT_DELAY_MS);
    }
  } else {
    if (pendingVerdictTimer != null) clearTimeout(pendingVerdictTimer);
    pendingVerdictTimer = null;
    if (pendingVerdictShown) clearVerdict();
    els.composer.placeholder = _originalPlaceholder;
    els.active?.removeAttribute('data-loading');
    resetComposerHint();
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

function setComposerHint(text) {
  if (els.hint) {
    els.hint.textContent = text;
    els.hint.classList?.toggle?.('is-error', Boolean(text && text !== DEFAULT_HINT));
  }
  setVoiceStatus(text === DEFAULT_HINT ? '' : text);
}

function resetComposerHint() {
  setComposerHint(DEFAULT_HINT);
}

function clearCompletionAction() {
  if (!hasRequiredElements()) return;
  completionHandler = null;
  els.active?.removeAttribute('data-complete');
  els.send.textContent = DEFAULT_SEND_LABEL;
  els.composer.placeholder = _originalPlaceholder;
  resetComposerHint();
}

function clearVerdict() {
  if (!bind() || !els.verdict) return;
  if (pendingVerdictTimer != null) clearTimeout(pendingVerdictTimer);
  pendingVerdictTimer = null;
  pendingVerdictShown = false;
  els.verdict.textContent = '';
  els.verdict.hidden = true;
}

function appendVerdict(text) {
  if (!bind() || !els.verdict) return;
  if (pendingVerdictTimer != null) clearTimeout(pendingVerdictTimer);
  pendingVerdictTimer = null;
  pendingVerdictShown = false;
  renderVerdict(text);
}

function renderVerdict(text) {
  const copy = String(text || '').trim();
  if (!copy) return;
  els.verdict.textContent = '';
  copy.split(' • ').forEach((segment, index) => {
    if (index > 0) {
      const sep = document.createElement('span');
      sep.className = 'drill-chamber__verdict-sep';
      sep.textContent = '•';
      els.verdict.appendChild(sep);
    }
    const part = document.createElement('span');
    part.className = 'drill-chamber__verdict-seg';
    part.textContent = segment;
    els.verdict.appendChild(part);
  });
  els.verdict.hidden = false;
}

function setCompletionAction(label = 'Return to concept', handler = null) {
  if (!bind()) return;
  stopSpeech();
  completionHandler = typeof handler === 'function' ? handler : exitHandler;
  els.active?.setAttribute('data-complete', 'true');
  els.composer.value = '';
  els.composer.disabled = true;
  els.send.disabled = false;
  els.send.textContent = label;
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

function storageGet(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function storageSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* preference just won't stick */
  }
}

function micPreferenceEnabled() {
  return storageGet(MIC_INPUT_PREF_KEY) !== '0';
}

function setVoiceStatus(text) {
  if (els.voiceStatus) els.voiceStatus.textContent = text || '';
}

function setMicListening(isListening) {
  listening = isListening;
  if (!els.mic) return;
  if (isListening) window.speechSynthesis?.cancel();
  els.mic.classList.toggle('is-listening', isListening);
  els.mic.setAttribute('aria-pressed', String(isListening));
  els.mic.setAttribute('aria-label', isListening ? 'Stop dictating answer' : 'Dictate answer');
}

function setTutorVoiceEnabled(enabled) {
  tutorVoiceEnabled = enabled;
  if (!els.tutorVoice) return;
  els.tutorVoice.classList.toggle('is-speaking', enabled);
  els.tutorVoice.setAttribute('aria-pressed', String(enabled));
  els.tutorVoice.setAttribute('aria-label', enabled ? 'Tutor voice on' : 'Tutor voice off');
  storageSet(TUTOR_VOICE_PREF_KEY, enabled ? '1' : '0');
}

function speakTutorQuestion(text) {
  const prompt = String(text || '').trim();
  if (!tutorVoiceEnabled || !prompt || prompt === lastSpokenQuestion) return;
  lastSpokenQuestion = prompt;
  window.speechSynthesis?.cancel();
  window.speechSynthesis?.speak(new window.SpeechSynthesisUtterance(prompt));
}

function stopSpeech() {
  if (listening) speechRecognition?.stop();
  window.speechSynthesis?.cancel();
}

function syncVoiceControls() {
  if (els.mic) {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    els.mic.hidden = !Recognition || !micPreferenceEnabled();
    els.mic.disabled = els.composer?.disabled || false;
  }
  if (els.tutorVoice) {
    const supported = Boolean(window.speechSynthesis && window.SpeechSynthesisUtterance);
    els.tutorVoice.hidden = !supported;
    if (supported) {
      setTutorVoiceEnabled(storageGet(TUTOR_VOICE_PREF_KEY) === '1');
    } else {
      tutorVoiceEnabled = false;
    }
  }
}

function initVoiceControls() {
  if (els.mic && !els.mic.dataset.voiceBound) {
    els.mic.dataset.voiceBound = 'true';
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (Recognition) {
      speechRecognition = new Recognition();
      speechRecognition.continuous = true;
      speechRecognition.interimResults = true;
      speechRecognition.lang = navigator.language || 'en-US';
      speechRecognition.addEventListener('start', () => {
        speechBaseText = els.composer.value.trim();
        setMicListening(true);
        setVoiceStatus('listening');
      });
      speechRecognition.addEventListener('result', (event) => {
        let transcript = '';
        for (let i = 0; i < event.results.length; i += 1) {
          transcript += event.results[i][0].transcript;
        }
        els.composer.value = [speechBaseText, transcript.trim()].filter(Boolean).join(' ');
      });
      speechRecognition.addEventListener('end', () => {
        setMicListening(false);
        setVoiceStatus('');
        els.composer.focus();
      });
      speechRecognition.addEventListener('error', (event) => {
        setMicListening(false);
        setVoiceStatus(event.error ? `voice input: ${event.error}` : 'voice input stopped');
      });
      els.mic.addEventListener('click', () => {
        if (els.mic.disabled) return;
        if (listening) {
          speechRecognition.stop();
          return;
        }
        try {
          speechRecognition.start();
        } catch {
          setMicListening(false);
        }
      });
    }
  }

  if (els.tutorVoice && !els.tutorVoice.dataset.voiceBound) {
    els.tutorVoice.dataset.voiceBound = 'true';
    els.tutorVoice.addEventListener('click', () => {
      const enabled = !tutorVoiceEnabled;
      setTutorVoiceEnabled(enabled);
      if (!enabled) window.speechSynthesis?.cancel();
      if (enabled) {
        lastSpokenQuestion = '';
        speakTutorQuestion(els.question?.textContent || '');
      }
    });
  }

  syncVoiceControls();
}

window.DrillChamber = {
  show, hide, appendHistoryTurn, swapQuestion,
  setComposerEnabled, setLoading, setCompletionAction,
  getComposerValue, clearComposer,
  appendCreed, appendVerdict, clearVerdict,
  onSend, onExit,
};
