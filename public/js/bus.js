// js/bus.js
export const Bus = (() => {
  const L = {};
  return {
    on:   (ev, fn) => (L[ev] ??= []).push(fn),
    emit: (ev, d)  => (L[ev]||[]).forEach(fn => fn(d)),
  };
})();
