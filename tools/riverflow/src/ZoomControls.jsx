import React from 'react';

export const ZOOM_MIN = 0.4;
export const ZOOM_MAX = 1.6;

export function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

export default function ZoomControls({ zoom, setZoom }) {
  return (
    <div className="zoom-controls">
      <button
        className="zoom-btn"
        onClick={() => setZoom((z) => clamp(z * 0.9, ZOOM_MIN, ZOOM_MAX))}
        aria-label="zoom out"
      >
        −
      </button>
      <span className="zoom-readout">{Math.round(zoom * 100)}%</span>
      <button
        className="zoom-btn"
        onClick={() => setZoom((z) => clamp(z * 1.1, ZOOM_MIN, ZOOM_MAX))}
        aria-label="zoom in"
      >
        +
      </button>
      <button
        className="zoom-btn zoom-reset"
        onClick={() => setZoom(1)}
        aria-label="reset zoom"
        title="reset zoom"
      >
        1:1
      </button>
    </div>
  );
}
