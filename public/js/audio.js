/**
 * Quiet sensory cues for threshold capture. Reading-room, not dashboard:
 * single soft sines, no chords, no celebration. On by default; toggle in
 * Settings (persisted to localStorage). Honors prefers-reduced-motion.
 */

const STORAGE_KEY = 'socratink:sound';

let audioCtx = null;
let lastKeyClickAt = 0;
let unlockBound = false;

function bindUnlock() {
  if (unlockBound || typeof window === 'undefined') return;
  unlockBound = true;
  const unlock = () => {
    ensureCtx();
    window.removeEventListener('pointerdown', unlock);
    window.removeEventListener('keydown', unlock);
  };
  window.addEventListener('pointerdown', unlock, { once: true, passive: true });
  window.addEventListener('keydown', unlock, { once: true, passive: true });
}

function readPreference() {
  try {
    // Default on — only an explicit "false" disables.
    return localStorage.getItem(STORAGE_KEY) !== 'false';
  } catch {
    return true;
  }
}

function reducedMotion() {
  return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function ensureCtx() {
  if (!audioCtx) {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    audioCtx = new Ctor();
  }
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}

function softTone({ freqStart, freqEnd, peak, attack = 0.008, decay = 0.12, type = 'sine' }) {
  const ctx = ensureCtx();
  if (!ctx) return;
  const t = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freqStart, t);
  if (freqEnd != null) osc.frequency.exponentialRampToValueAtTime(freqEnd, t + decay);
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(peak, t + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + decay);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t);
  osc.stop(t + decay + 0.02);
}

if (readPreference()) bindUnlock();

export const AudioFX = {
  enabled: readPreference(),

  init() { ensureCtx(); },

  setEnabled(value) {
    this.enabled = Boolean(value);
    try { localStorage.setItem(STORAGE_KEY, String(this.enabled)); } catch {}
    if (this.enabled) {
      ensureCtx();
      bindUnlock();
    }
  },

  playFocusTap() {
    if (!this.enabled || reducedMotion()) return;
    softTone({ freqStart: 220, freqEnd: 110, peak: 0.08, decay: 0.14 });
  },

  playKeyClick() {
    if (!this.enabled || reducedMotion()) return;
    const now = performance.now();
    if (now - lastKeyClickAt < 90) return;
    lastKeyClickAt = now;
    softTone({ type: 'triangle', freqStart: 620, freqEnd: 280, peak: 0.025, decay: 0.05 });
  },

  // Threshold submit is capture, not celebration — single low settle, no chord.
  playSubmitChime() {
    if (!this.enabled || reducedMotion()) return;
    softTone({ freqStart: 392, freqEnd: 261.63, peak: 0.14, decay: 0.7 }); // G4 → C4 settle
  },
};
