import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useGitGraph } from './useGitGraph.js';
import RiverCanvas from './RiverCanvas.jsx';
import ActionPopover from './ActionPopover.jsx';
import ChatPanel from './ChatPanel.jsx';
import { createBranch, createPull, mergePull, repoCoords } from './api.js';

import ZoomControls, { ZOOM_MIN, ZOOM_MAX, clamp } from './ZoomControls.jsx';
import HelpButton from './HelpButton.jsx';

const MAIN = import.meta.env.VITE_MAIN_BRANCH || 'main';
const DRAG_THRESHOLD = 4;

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


