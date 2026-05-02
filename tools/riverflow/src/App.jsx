import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useGitGraph } from './useGitGraph.js';
import RiverCanvas from './RiverCanvas.jsx';
import ActionPopover from './ActionPopover.jsx';
import ChatPanel from './ChatPanel.jsx';
import { createBranch, createPull, mergePull, repoCoords } from './api.js';

const MAIN = import.meta.env.VITE_MAIN_BRANCH || 'main';
const ZOOM_MIN = 0.4;
const ZOOM_MAX = 1.6;
const DRAG_THRESHOLD = 4;

function clamp(v, lo, hi) {
  return Math.max(lo, Math.min(hi, v));
}

export default function App() {
  const { graph, error, loading, refresh, addOptimistic, transitions } =
    useGitGraph();
  const [action, setAction] = useState(null);
  const [zoom, setZoom] = useState(1);
  const [chatOpen, setChatOpen] = useState(false);

  const hostRef = useRef(null);
  const didAutoScroll = useRef(false);
  const dragRef = useRef({ active: false });

  // Auto-scroll to "now" once the first graph is rendered.
  useLayoutEffect(() => {
    if (didAutoScroll.current) return;
    if (!graph || !hostRef.current) return;
    const c = hostRef.current;
    c.scrollLeft = c.scrollWidth - c.clientWidth;
    didAutoScroll.current = true;
  }, [graph]);

  // Drag-to-pan on the canvas host. Click-suppression on drag end.
  useEffect(() => {
    const c = hostRef.current;
    if (!c) return;

    function onMouseDown(e) {
      if (e.button !== 0) return;
      // Don't preventDefault — let the click happen naturally if no drag.
      dragRef.current = {
        active: true,
        startX: e.clientX,
        startY: e.clientY,
        scrollLeft: c.scrollLeft,
        scrollTop: c.scrollTop,
        moved: false,
      };
    }

    function onMouseMove(e) {
      const d = dragRef.current;
      if (!d.active) return;
      const dx = e.clientX - d.startX;
      const dy = e.clientY - d.startY;
      if (!d.moved && Math.abs(dx) < DRAG_THRESHOLD && Math.abs(dy) < DRAG_THRESHOLD) return;
      d.moved = true;
      c.style.cursor = 'grabbing';
      c.scrollLeft = d.scrollLeft - dx;
      c.scrollTop = d.scrollTop - dy;
    }

    function onMouseUp() {
      const d = dragRef.current;
      d.active = false;
      c.style.cursor = '';
      if (d.moved) {
        // Suppress the upcoming click so it doesn't open a commit URL etc.
        const suppress = (ev) => {
          ev.stopPropagation();
          ev.preventDefault();
        };
        window.addEventListener('click', suppress, { capture: true, once: true });
        // Safety: drop the listener if no click ever fires.
        setTimeout(
          () => window.removeEventListener('click', suppress, { capture: true }),
          80,
        );
      }
    }

    c.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      c.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  // ⌘/Ctrl + wheel = zoom, mouse-anchored.
  useEffect(() => {
    const c = hostRef.current;
    if (!c) return;
    function onWheel(e) {
      if (!(e.metaKey || e.ctrlKey)) return;
      e.preventDefault();
      const factor = e.deltaY > 0 ? 0.92 : 1.08;
      setZoom((z) => {
        const next = clamp(z * factor, ZOOM_MIN, ZOOM_MAX);
        if (next === z) return z;
        // Anchor zoom to the mouse position.
        const rect = c.getBoundingClientRect();
        const pointerX = e.clientX - rect.left + c.scrollLeft;
        const pointerY = e.clientY - rect.top + c.scrollTop;
        requestAnimationFrame(() => {
          c.scrollLeft = (pointerX * next) / z - (e.clientX - rect.left);
          c.scrollTop = (pointerY * next) / z - (e.clientY - rect.top);
        });
        return next;
      });
    }
    c.addEventListener('wheel', onWheel, { passive: false });
    return () => c.removeEventListener('wheel', onWheel);
  }, []);

  async function handleSubmit(payload) {
    if (payload.kind === 'create-branch') {
      await createBranch(payload.name, payload.sha);
      addOptimistic({ kind: 'branch', name: payload.name, fromSha: payload.sha });
    } else if (payload.kind === 'open-pr') {
      await createPull({
        title: payload.title,
        body: payload.body,
        head: payload.head,
        base: payload.base,
      });
      addOptimistic({
        kind: 'pr',
        title: payload.title,
        head: payload.head,
        base: payload.base,
      });
    } else if (payload.kind === 'merge-pr') {
      await mergePull(payload.number);
      addOptimistic({ kind: 'merge', number: payload.number });
    }
    setAction(null);
    refresh();
  }

  const missingEnv =
    !import.meta.env.VITE_GITHUB_TOKEN ||
    !import.meta.env.VITE_GITHUB_OWNER ||
    !import.meta.env.VITE_GITHUB_REPO;

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">riverflow</span>
        </div>
        <div className="repo">
          {repoCoords.owner}/{repoCoords.repo}
          <span className="dot">·</span>
          <span className="muted">{MAIN}</span>
        </div>
        <div className="status">
          {loading && <span className="status-loading">loading…</span>}
          {error && <span className="status-error">{error}</span>}
          {!loading && !error && graph && (
            <span className="status-ok">
              {graph.main.length} main · {graph.branches.length} branches ·{' '}
              {graph.pulls.length} PRs
            </span>
          )}
          <ZoomControls zoom={zoom} setZoom={setZoom} />
          <button
            className={`chat-toggle ${chatOpen ? 'is-open' : ''}`}
            onClick={() => setChatOpen((v) => !v)}
            aria-label="toggle chat"
            aria-pressed={chatOpen}
          >
            chat
          </button>
          <HelpButton />
          <button className="refresh-btn" onClick={refresh} disabled={loading}>
            refresh
          </button>
        </div>
      </header>

      {missingEnv && (
        <div className="env-warning">
          Missing env vars. Copy <code>.env.example</code> to <code>.env</code>{' '}
          and fill in <code>VITE_GITHUB_TOKEN</code>,{' '}
          <code>VITE_GITHUB_OWNER</code>, <code>VITE_GITHUB_REPO</code>.
        </div>
      )}

      <div className={`canvas-row ${chatOpen ? 'with-chat' : ''}`}>
        <main className="canvas-host" ref={hostRef}>
          <RiverCanvas
            graph={graph}
            transitions={transitions}
            mainBranch={MAIN}
            zoom={zoom}
            onAction={setAction}
          />
        </main>
        <ChatPanel
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          graph={graph}
          mainBranch={MAIN}
        />
      </div>

      <ActionPopover
        action={action}
        onClose={() => setAction(null)}
        onSubmit={handleSubmit}
      />
    </div>
  );
}

function ZoomControls({ zoom, setZoom }) {
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

function HelpButton() {
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
