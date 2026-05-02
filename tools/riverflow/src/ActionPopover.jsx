import React, { useState } from 'react';

export default function ActionPopover({ action, onClose, onSubmit }) {
  if (!action) return null;
  return (
    <div
      className="popover-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="popover"
        style={{ left: action.screenX, top: action.screenY }}
      >
        {action.kind === 'create-branch' && (
          <CreateBranchForm
            commit={action.commit}
            onCancel={onClose}
            onSubmit={onSubmit}
          />
        )}
        {action.kind === 'open-pr' && (
          <OpenPRForm
            branch={action.branch}
            mainBranch={action.mainBranch}
            onCancel={onClose}
            onSubmit={onSubmit}
          />
        )}
        {action.kind === 'merge-pr' && (
          <MergePRForm
            pr={action.pr}
            onCancel={onClose}
            onSubmit={onSubmit}
          />
        )}
      </div>
    </div>
  );
}

function CreateBranchForm({ commit, onCancel, onSubmit }) {
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!name.trim()) return;
        setBusy(true);
        setErr(null);
        try {
          await onSubmit({ kind: 'create-branch', name: name.trim(), sha: commit.sha });
        } catch (ex) {
          setErr(ex.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>Branch from {commit.short}</h3>
      <p className="popover-sub">{commit.message?.split('\n')[0]?.slice(0, 80)}</p>
      <input
        autoFocus
        placeholder="branch-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        spellCheck={false}
      />
      {err && <div className="popover-err">{err}</div>}
      <div className="popover-actions">
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="submit" disabled={busy || !name.trim()}>
          {busy ? 'creating…' : 'create'}
        </button>
      </div>
    </form>
  );
}

function OpenPRForm({ branch, mainBranch, onCancel, onSubmit }) {
  const [title, setTitle] = useState(branch.name.replace(/[-_/]/g, ' '));
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        if (!title.trim()) return;
        setBusy(true);
        setErr(null);
        try {
          await onSubmit({
            kind: 'open-pr',
            head: branch.name,
            base: mainBranch,
            title: title.trim(),
            body,
          });
        } catch (ex) {
          setErr(ex.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>Open PR · {branch.name} → {mainBranch}</h3>
      <p className="popover-sub">+{branch.ahead} ahead / {branch.behind} behind</p>
      <input
        autoFocus
        placeholder="title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
      />
      <textarea
        placeholder="body (optional)"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={4}
      />
      {err && <div className="popover-err">{err}</div>}
      <div className="popover-actions">
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="submit" disabled={busy || !title.trim()}>
          {busy ? 'opening…' : 'open PR'}
        </button>
      </div>
    </form>
  );
}

function MergePRForm({ pr, onCancel, onSubmit }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setErr(null);
        try {
          await onSubmit({ kind: 'merge-pr', number: pr.number });
        } catch (ex) {
          setErr(ex.message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>Merge #{pr.number}</h3>
      <p className="popover-sub">{pr.title}</p>
      <p className="popover-sub">
        {pr.head} → {pr.base} · merge commit
      </p>
      {err && <div className="popover-err">{err}</div>}
      <div className="popover-actions">
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="submit" disabled={busy}>
          {busy ? 'merging…' : 'merge'}
        </button>
      </div>
    </form>
  );
}
