/**
 * Quiet sensory cues for socratink.
 * Reading-room, not dashboard. Material, not musical.
 *
 * Recipes are tuned by ear and ported here directly. Re-tune in place when
 * a sound needs to change; the historical sound-lab page is no longer shipped.
 *
 *   typing       playKeyClick       F·brush   lowpass noise 600Hz, 18ms
 *   focus tab    playFocusTap       I·breath  highpass noise 5kHz, 10ms
 *   tile-click   playTileClick      D·thud    60Hz square + bandpass noise
 *   drawer       playDrawerToggle   F·body    lowpass cloth, 1.1kHz, 30ms
 *   threshold    playSubmitChime    (unchanged — long G4→C4 settle)
 *
 * On by default; toggle in Settings. Honors prefers-reduced-motion.
 */

import { prefersReducedMotion } from './motion.js';

const STORAGE_KEY = 'socratink:sound';

// Compensates for the /_lab/ master-gain default at 0.7. Apply at recipe
// peak so the effective output matches what was auditioned in the lab.
const LAB_MASTER_GAIN = 0.7;

let audioCtx = null;
let lastKeyClickAt = 0;
let lastFocusTapAt = 0;
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
    return localStorage.getItem(STORAGE_KEY) !== 'false';
  } catch {
    return true;
  }
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
  if (freqEnd != null) osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), t + decay);
  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(peak, t + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + decay);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(t);
  osc.stop(t + decay + 0.02);
}

function noiseBurst({ duration = 0.015, peak = 0.4, filter = null }) {
  const ctx = ensureCtx();
  if (!ctx) return;
  const t = ctx.currentTime;
  const buf = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * duration), ctx.sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
  const src = ctx.createBufferSource();
  src.buffer = buf;
  const g = ctx.createGain();
  g.gain.setValueAtTime(peak, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + duration);
  let last = src;
  if (filter) {
    const f = ctx.createBiquadFilter();
    f.type = filter.type;
    f.frequency.value = filter.freq;
    if (filter.q != null) f.Q.value = filter.q;
    src.connect(f);
    last = f;
  }
  last.connect(g);
  g.connect(ctx.destination);
  src.start(t);
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

  // I·breath (dampened) — paper-rustle, ethereal. Used for form-field
  // focus traversal AND sidebar / bottom-nav clicks. Highpass cutoff
  // lowered from 5000 → 4000Hz to take the edge off the "hiss." 150ms
  // throttle so a nav-click + auto-focus on a view doesn't double-fire.
  playFocusTap() {
    if (!this.enabled || prefersReducedMotion()) return;
    const now = performance.now();
    if (now - lastFocusTapAt < 150) return;
    lastFocusTapAt = now;
    noiseBurst({
      duration: 0.010,
      peak: 0.38 * LAB_MASTER_GAIN,
      filter: { type: 'highpass', freq: 4000 },
    });
  },

  // F·brush — velvet click, lowpass cloth. Frequent (per-keystroke) → throttled.
  playKeyClick() {
    if (!this.enabled || prefersReducedMotion()) return;
    const now = performance.now();
    if (now - lastKeyClickAt < 90) return;
    lastKeyClickAt = now;
    noiseBurst({
      duration: 0.018,
      peak: 0.28 * LAB_MASTER_GAIN,
      filter: { type: 'lowpass', freq: 600, q: 0.8 },
    });
  },

  // D·thud — mechanical key, weighty. Used for deliberate tile-click on the desk board.
  playTileClick() {
    if (!this.enabled || prefersReducedMotion()) return;
    softTone({
      type: 'square',
      freqStart: 60,
      peak: 0.14 * LAB_MASTER_GAIN,
      attack: 0.001,
      decay: 0.022,
    });
    noiseBurst({
      duration: 0.025,
      peak: 0.18 * LAB_MASTER_GAIN,
      filter: { type: 'bandpass', freq: 1800, q: 2.5 },
    });
  },

  // F·body — velvet click with presence. Lowpass cloth, no tonal ping.
  // Used for drawer open/close: reads as fabric reveal, distinct from
  // F·brush (typing) by way of longer duration + higher lowpass cutoff.
  playDrawerToggle() {
    if (!this.enabled || prefersReducedMotion()) return;
    noiseBurst({
      duration: 0.030,
      peak: 0.34 * LAB_MASTER_GAIN,
      filter: { type: 'lowpass', freq: 1100, q: 1.2 },
    });
  },

  // Threshold submit is capture, not celebration — single low settle, no chord.
  playSubmitChime() {
    if (!this.enabled || prefersReducedMotion()) return;
    softTone({ freqStart: 392, freqEnd: 261.63, peak: 0.14, decay: 0.7 }); // G4 → C4 settle
  },
};
