/**
 * Shared reduced-motion check.
 *
 * Returns true when EITHER the user has set `socratink.motion = "reduced"`
 * via Settings (surfaced as `html[data-motion="reduced"]`) OR the OS
 * prefers reduced motion. The user override is additive: it can force
 * quiet motion even when the OS does not request it.
 *
 * Loaded as an ES module by app.js / concept-create.js / graph-view.js.
 * The same module also binds the helper on the window so
 * the classic-script `intro-particles.js` can read it without an import.
 */

export function prefersReducedMotion() {
  if (typeof document !== 'undefined') {
    const motionAttr = document.documentElement?.dataset?.motion;
    if (motionAttr === 'reduced') return true;
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    try {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (err) {
      return false;
    }
  }
  return false;
}

if (typeof window !== 'undefined') {
  window.SocratinkMotion = Object.freeze({ prefersReducedMotion });
}
