import React, { useEffect, useRef, useState } from 'react';
import { chat, hasGeminiKey } from './gemini.js';
import { buildSystemInstruction } from './buildChatContext.js';
import { repoCoords } from './api.js';

const SUGGESTIONS = [
  'summarize what just landed on main',
  'what branches need attention?',
  'any open PRs blocked or stale?',
];

export default function ChatPanel({ open, onClose, graph, mainBranch }) {
  const [history, setHistory] = useState([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history, busy, error]);

  async function send(text) {
    const msg = text.trim();
    if (!msg || busy) return;
    setBusy(true);
    setError(null);
    setInput('');
    // Cap history to last 20 messages — both displayed and shipped — so long
    // sessions don't bloat request size.
    const sentHistory = history.slice(-20);
    const userMsg = { role: 'user', text: msg };
    setHistory((h) => [...h.slice(-19), userMsg]);
    try {
      const reply = await chat({
        history: sentHistory,
        systemInstruction: buildSystemInstruction(graph, repoCoords, mainBranch),
        message: msg,
      });
      setHistory((h) => [...h.slice(-19), { role: 'model', text: reply }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  if (!open) return null;

  const noKey = !hasGeminiKey();

  return (
    <aside className="chat-panel" role="complementary" aria-label="chat">
      <header className="chat-head">
        <span className="chat-title">
          chat <span className="chat-model">· gemini-2.5-flash</span>
        </span>
        <div className="chat-head-actions">
          {history.length > 0 && (
            <button
              className="chat-clear"
              onClick={() => {
                setHistory([]);
                setError(null);
              }}
              title="clear conversation"
            >
              clear
            </button>
          )}
          <button className="chat-close" onClick={onClose} aria-label="close">
            ×
          </button>
        </div>
      </header>

      {noKey ? (
        <div className="chat-empty">
          <p className="muted">
            No Gemini key configured. Save one to{' '}
            <code>~/.config/riverflow/gemini-token</code> and restart the
            launcher.
          </p>
        </div>
      ) : (
        <>
          <div className="chat-scroll" ref={scrollRef}>
            {history.length === 0 && (
              <div className="chat-empty">
                <p className="muted">
                  Ask about the current graph state. Each turn ships a fresh
                  snapshot — no memory between sessions.
                </p>
                <div className="chat-suggestions">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      className="chat-suggestion"
                      onClick={() => send(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {history.map((m, i) => (
              <div key={i} className={`chat-msg chat-msg-${m.role}`}>
                <div className="chat-msg-role">
                  {m.role === 'user' ? 'you' : 'gemini'}
                </div>
                <div className="chat-msg-body">{m.text}</div>
              </div>
            ))}
            {busy && (
              <div className="chat-msg chat-msg-model">
                <div className="chat-msg-role">gemini</div>
                <div className="chat-msg-body chat-thinking">
                  <span /><span /><span />
                </div>
              </div>
            )}
            {error && <div className="chat-error">{error}</div>}
          </div>

          <div className="chat-input">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="ask about this repo…  (Enter to send · Shift+Enter for newline)"
              rows={2}
              disabled={busy}
              spellCheck={false}
            />
            <button
              className="chat-send"
              onClick={() => send(input)}
              disabled={busy || !input.trim()}
            >
              send
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
