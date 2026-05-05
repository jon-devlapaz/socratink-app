/**
 * Quiet sensory cues for threshold capture. Reading-room, not dashboard:
 * single soft sines, no chords, no celebration. Off by default; opt-in via
 * Settings (persisted to localStorage). Honors prefers-reduced-motion.
 */

const STORAGE_KEY = 'socratink:sound';

let audioCtx = null;
let lastKeyClickAt = 0;

function readPreference() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true';
  } catch {
    return false;
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

export const AudioFX = {
  enabled: readPreference(),

  init() { ensureCtx(); },

  setEnabled(value) {
    this.enabled = Boolean(value);
    try { localStorage.setItem(STORAGE_KEY, String(this.enabled)); } catch {}
    if (this.enabled) ensureCtx();
  },

  playFocusTap() {
    if (!this.enabled || reducedMotion()) return;
    softTone({ freqStart: 180, freqEnd: 90, peak: 0.025, decay: 0.10 });
  },

  playKeyClick() {
    if (!this.enabled || reducedMotion()) return;
    const now = performance.now();
    if (now - lastKeyClickAt < 90) return;
    lastKeyClickAt = now;
    softTone({ type: 'triangle', freqStart: 520, freqEnd: 260, peak: 0.006, decay: 0.04 });
  },

  // Threshold submit is capture, not celebration — single low settle, no chord.
  playSubmitChime() {
    if (!this.enabled || reducedMotion()) return;
    softTone({ freqStart: 392, freqEnd: 261.63, peak: 0.04, decay: 0.55 }); // G4 → C4 settle
  },
};
