// js/morph.js
import { GEO, easeInOutCubic, interpCoords, coordsToPoints } from './geo.js';

// polygons[tileIdx][polyIdx] — rebuilt by renderGrid()
export const crystalPolygons = [null, null, null, null];

export const Morph = (() => {
  const DUR = 620;
  let tasks = [];
  let raf   = null;

  function tick(now) {
    tasks = tasks.filter(task => {
      if (!task.t0) task.t0 = now;
      const t = easeInOutCubic(Math.min((now-task.t0)/DUR, 1));
      task.polys.forEach((el,i) => {
        if (el) el.setAttribute('points', coordsToPoints(interpCoords(task.from[i], task.to[i], t)));
      });
      return t < 1;
    });
    if (tasks.length > 0) { raf = requestAnimationFrame(tick); }
    else                  { raf = null; }
  }

  return {
    start(tileIdx, fromState, toState) {
      // Cancel any existing task for this tile
      tasks = tasks.filter(t => t.idx !== tileIdx);
      tasks.push({
        idx:   tileIdx,
        polys: crystalPolygons[tileIdx] || [],
        from:  GEO[fromState],
        to:    GEO[toState],
        t0:    null,
      });
      if (!raf) raf = requestAnimationFrame(tick);
    },
    snap(tileIdx, state) {
      // Remove any pending task for this tile
      tasks = tasks.filter(t => t.idx !== tileIdx);
      const polys = crystalPolygons[tileIdx];
      if (!polys) return;
      GEO[state].forEach((coords,i) => {
        if (polys[i]) polys[i].setAttribute('points', coordsToPoints(coords));
      });
    },
  };
})();
