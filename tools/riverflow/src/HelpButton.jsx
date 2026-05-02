import React, { useState, useRef, useEffect } from 'react';

export default function HelpButton() {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onDocClick(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  return (
    <div className="help-wrap" ref={wrapRef}>
      <button
        type="button"
        className="help-btn"
        onClick={() => setOpen((v) => !v)}
        aria-label="help"
        aria-expanded={open}
      >
        ?
      </button>
      {open && (
        <div className="help-popover" role="dialog">
          <div className="help-row">
            <span className="help-gesture">drag canvas</span>
            <span className="help-arrow">→</span>
            <span className="help-action">pan</span>
          </div>
          <div className="help-row">
            <span className="help-gesture">⌘-scroll</span>
            <span className="help-arrow">→</span>
            <span className="help-action">zoom</span>
          </div>
          <div className="help-row">
            <span className="help-gesture">click commit</span>
            <span className="help-arrow">→</span>
            <span className="help-action">open on github</span>
          </div>
          <div className="help-row">
            <span className="help-gesture">right-click commit</span>
            <span className="help-arrow">→</span>
            <span className="help-action">branch</span>
          </div>
          <div className="help-row">
            <span className="help-gesture">click branch label</span>
            <span className="help-arrow">→</span>
            <span className="help-action">open PR</span>
          </div>
          <div className="help-row">
            <span className="help-gesture">click open PR arc</span>
            <span className="help-arrow">→</span>
            <span className="help-action">merge</span>
          </div>
        </div>
      )}
    </div>
  );
}
