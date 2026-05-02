import React, { useState } from 'react';
import CommitNode, { CommitTooltip } from './CommitNode.jsx';
import BranchLabel from './BranchLabel.jsx';
import PRCard from './PRCard.jsx';

const X_STEP = 90;
const Y_STEP = 110;
const LEFT_PAD = 80;
const RIGHT_PAD = 220;
const TOP_PAD = 160;
const BOTTOM_PAD = 160;

const EMPTY_TRANSITIONS = {
  newPRs: new Set(),
  mergedPRs: new Set(),
  branchTipChanges: new Set(),
};

export default function RiverCanvas({
  graph,
  transitions = EMPTY_TRANSITIONS,
  mainBranch,
  zoom = 1,
  onAction,
}) {
  const [hover, setHover] = useState(null); // { node, cx, cy } | null
  if (!graph) return null;
  const { main, branches, pulls, mainTipX } = graph;
  const handleHover = (node, cx, cy) =>
    setHover(node ? { node, cx, cy } : null);

  const lanes = branches.map((b) => b.lane);
  const maxLane = lanes.length ? Math.max(0, ...lanes) : 0;
  const minLane = lanes.length ? Math.min(0, ...lanes) : 0;

  const mainY = TOP_PAD + maxLane * Y_STEP;
  const height = mainY + Math.abs(minLane) * Y_STEP + BOTTOM_PAD;
  const gridW = mainTipX + 2;
  const width = LEFT_PAD + gridW * X_STEP + RIGHT_PAD;

  const xOf = (gx) => LEFT_PAD + gx * X_STEP;
  const yOf = (lane) => mainY - lane * Y_STEP;

  const mainStart = xOf(0);
  const mainEnd = xOf(mainTipX);

  return (
    <svg
      width={width * zoom}
      height={height * zoom}
      viewBox={`0 0 ${width} ${height}`}
      className="river-canvas"
    >
      <defs>
        <linearGradient id="riverFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#5a4a82" />
          <stop offset="100%" stopColor="#2c2545" />
        </linearGradient>
        <linearGradient id="streamFill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="#3b3458" />
          <stop offset="100%" stopColor="#251f3a" />
        </linearGradient>
      </defs>

      {/* River — main */}
      <path
        d={`M ${mainStart - 30} ${mainY} L ${mainEnd + 30} ${mainY}`}
        stroke="url(#riverFill)"
        strokeWidth={26}
        strokeLinecap="round"
        fill="none"
        opacity={0.96}
      />
      <path
        d={`M ${mainStart - 30} ${mainY} L ${mainEnd + 30} ${mainY}`}
        stroke="#cac4ce"
        strokeWidth={2}
        strokeDasharray="3 18"
        strokeLinecap="round"
        fill="none"
        className="river-flow"
        opacity={0.55}
      />
      <path
        d={`M ${mainStart - 30} ${mainY - 4} L ${mainEnd + 30} ${mainY - 4}`}
        stroke="#f7ece1"
        strokeWidth={1}
        strokeDasharray="1 30"
        strokeLinecap="round"
        fill="none"
        className="river-flow river-flow-fast"
        opacity={0.42}
      />

      {/* Main label */}
      <text x={mainStart - 50} y={mainY + 5} className="branch-label" fill="#cac4ce" textAnchor="end">
        {mainBranch}
      </text>

      {/* Branch streams — only branches with commits ahead of main */}
      {branches.filter((b) => b.ahead > 0).map((b) => {
        const fx = xOf(b.forkX);
        const ly = yOf(b.lane);
        const lastX = xOf(b.commits[b.commits.length - 1].x);
        const path = `
          M ${fx} ${mainY}
          C ${fx + X_STEP / 3} ${mainY}, ${fx + X_STEP / 3} ${ly}, ${fx + X_STEP / 2} ${ly}
          L ${lastX + 24} ${ly}
        `;
        return (
          <g
            key={b.name}
            className="branch-stream"
            style={{ opacity: b.optimistic ? 0.6 : 1 }}
          >
            <path
              d={path}
              stroke="url(#streamFill)"
              strokeWidth={14}
              strokeLinecap="round"
              fill="none"
            />
            <path
              d={path}
              stroke={b.color}
              strokeWidth={1.5}
              strokeDasharray="2 14"
              strokeLinecap="round"
              fill="none"
              className="river-flow"
              opacity={0.55}
            />
          </g>
        );
      })}

      {/* Now edge */}
      <line
        x1={mainEnd + 14}
        y1={TOP_PAD - 80}
        x2={mainEnd + 14}
        y2={height - 60}
        stroke="#8d86c9"
        strokeWidth={1}
        strokeDasharray="4 4"
        opacity={0.32}
      />
      <text
        x={mainEnd + 14}
        y={TOP_PAD - 88}
        textAnchor="middle"
        className="now-label"
      >
        now
      </text>

      {/* PR confluences — only for branches with horizontal spread.
          At-main branches fold PR state into the pin instead. */}
      {pulls.map((pr) => {
        if (!pr.branch) return null;
        if (pr.branch.ahead === 0) return null;
        const tipX = xOf(pr.branch.tip.x);
        const tipY = yOf(pr.branch.lane);
        const targetX = mainEnd + 12;
        const isNew = transitions.newPRs.has(pr.number);
        const justMerged = transitions.mergedPRs.has(pr.number);
        return (
          <PRCard
            key={pr.number}
            pr={pr}
            fromX={tipX}
            fromY={tipY}
            toX={targetX}
            toY={mainY}
            isNew={isNew}
            justMerged={justMerged}
            onClick={(p, e) =>
              p.state === 'open'
                ? onAction({
                    kind: 'merge-pr',
                    pr: p,
                    screenX: e.clientX,
                    screenY: e.clientY,
                  })
                : null
            }
          />
        );
      })}

      {/* Commit nodes — main */}
      {main.map((node) => (
        <CommitNode
          key={node.sha}
          node={node}
          cx={xOf(node.x)}
          cy={mainY}
          color="#cac4ce"
          isHovered={hover?.node.sha === node.sha}
          onHover={handleHover}
          onContextMenu={(n, e) =>
            onAction({
              kind: 'create-branch',
              commit: n,
              screenX: e.clientX,
              screenY: e.clientY,
            })
          }
        />
      ))}

      {/* Commit nodes — branches; tip pulses when branch headSha just changed */}
      {branches.map((b) =>
        b.commits.map((node, idx) => {
          const isTip = idx === b.commits.length - 1;
          const pulse = isTip && transitions.branchTipChanges.has(b.name);
          return (
            <CommitNode
              key={`${b.name}:${node.sha}`}
              node={node}
              cx={xOf(node.x)}
              cy={yOf(b.lane)}
              color={b.color}
              isHovered={hover?.node.sha === node.sha}
              optimistic={b.optimistic}
              pulse={pulse}
              onHover={handleHover}
              onContextMenu={(n, e) =>
                onAction({
                  kind: 'create-branch',
                  commit: n,
                  screenX: e.clientX,
                  screenY: e.clientY,
                })
              }
            />
          );
        }),
      )}

      {/* Single shared tooltip — only one can be alive */}
      {hover && (
        <CommitTooltip node={hover.node} cx={hover.cx} cy={hover.cy} />
      )}

      {/* Branch labels — branches with commits ahead get full label at tip */}
      {branches.filter((b) => b.ahead > 0).map((b) => {
        const tipX = xOf(b.tip.x);
        const tipY = yOf(b.lane);
        const openPR =
          pulls.find((p) => p.head === b.name && p.state === 'open') || null;
        return (
          <BranchLabel
            key={b.name}
            branch={b}
            x={tipX}
            y={tipY}
            openPR={openPR}
            onClick={(branch, e) =>
              onAction({
                kind: 'open-pr',
                branch,
                mainBranch,
                screenX: e.clientX,
                screenY: e.clientY,
              })
            }
          />
        );
      })}

      {/* At-main branches: floating pins perched above the merge base */}
      {branches
        .filter((b) => b.ahead === 0)
        .map((b, i) => {
          const x = xOf(b.forkX);
          const yOffset = 36 + i * 26;
          const labelY = mainY - yOffset;
          const pulse = transitions.branchTipChanges.has(b.name);
          const pr = pulls.find((p) => p.head === b.name) || null;
          const isNewPR = pr && transitions.newPRs.has(pr.number);
          const justMerged = pr && transitions.mergedPRs.has(pr.number);
          return (
            <AtMainPin
              key={b.name}
              branch={b}
              x={x}
              labelY={labelY}
              mainY={mainY}
              pulse={pulse}
              pr={pr}
              isNewPR={isNewPR}
              justMerged={justMerged}
              onClick={(e) =>
                pr && pr.state === 'open'
                  ? onAction({
                      kind: 'merge-pr',
                      pr,
                      screenX: e.clientX,
                      screenY: e.clientY,
                    })
                  : onAction({
                      kind: 'open-pr',
                      branch: b,
                      mainBranch,
                      screenX: e.clientX,
                      screenY: e.clientY,
                    })
              }
            />
          );
        })}
    </svg>
  );
}

const PR_COLORS = {
  open: '#d8a867',   // amber — drilled state
  merged: '#4dba8a', // success
  closed: '#7a7387',
};

function AtMainPin({
  branch,
  x,
  labelY,
  mainY,
  pulse = false,
  pr = null,
  isNewPR = false,
  justMerged = false,
  onClick,
}) {
  const [hover, setHover] = useState(false);
  const w = Math.max(branch.name.length * 7 + 20, 60);
  const h = 18;

  let outlineColor = branch.color;
  if (pr) {
    if (pr.merged) outlineColor = PR_COLORS.merged;
    else if (pr.state === 'open') outlineColor = PR_COLORS.open;
  }

  const isOpenPR = pr && pr.state === 'open' && !pr.merged;
  // The pin always has an action: merge if there's an open PR, else open-PR.
  const interactive = true;

  let hintText = null;
  let hintMuted = false;
  if (hover) {
    if (isOpenPR) {
      const num = pr.number > 0 ? `#${pr.number}` : '#…';
      hintText = `merge PR ${num} →`;
    } else {
      hintText = 'open PR →';
    }
  }

  return (
    <g
      style={{
        cursor: interactive ? 'pointer' : 'default',
        opacity: branch.optimistic || pr?.optimistic ? 0.6 : 1,
      }}
      onClick={interactive ? onClick : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <line
        x1={x}
        y1={mainY - 6}
        x2={x}
        y2={labelY + h / 2}
        stroke={branch.color}
        strokeWidth={1}
        opacity={0.45}
        strokeDasharray="2 3"
      />
      <circle
        cx={x}
        cy={mainY}
        r={3}
        fill={outlineColor}
        opacity={0.85}
        className={pulse ? 'tip-pulse' : undefined}
      />
      <rect
        x={x - w / 2}
        y={labelY - h / 2}
        width={w}
        height={h}
        rx={6}
        fill="#2a2542"
        stroke={outlineColor}
        strokeWidth={pr ? 1.4 : 1}
        className={
          pr && pr.state === 'open' && !pr.merged ? 'pin-pr-open' : undefined
        }
        style={{ transition: 'stroke 400ms ease' }}
      />
      <text
        x={x}
        y={labelY + 3}
        textAnchor="middle"
        className="branch-label"
        fill={outlineColor}
        style={{ fontSize: 10 }}
      >
        {branch.name}
      </text>

      {/* Subtle "this branch has a PR" indicator next to the name */}
      {pr && (
        <circle
          cx={x + w / 2 - 6}
          cy={labelY}
          r={2}
          fill={pr.merged ? PR_COLORS.merged : PR_COLORS.open}
        />
      )}

      {/* New-PR draw-on: a brief outline pulse, mirroring the arc draw-on */}
      {isNewPR && (
        <rect
          x={x - w / 2}
          y={labelY - h / 2}
          width={w}
          height={h}
          rx={5}
          fill="none"
          stroke={PR_COLORS.open}
          strokeWidth={1.4}
          className="pin-drawon"
        />
      )}

      {/* Merge ripple at the pin's anchor on main */}
      {justMerged && (
        <g pointerEvents="none">
          <circle cx={x} cy={mainY} r={0} fill="none" stroke={PR_COLORS.merged} strokeWidth={2} opacity={0.9}>
            <animate attributeName="r" from="0" to="56" dur="0.8s" fill="freeze" />
            <animate attributeName="opacity" from="0.9" to="0" dur="0.8s" fill="freeze" />
          </circle>
          <circle cx={x} cy={mainY} r={0} fill={PR_COLORS.merged} opacity={0.5}>
            <animate attributeName="r" from="0" to="14" dur="0.4s" fill="freeze" />
            <animate attributeName="opacity" from="0.6" to="0" dur="0.8s" fill="freeze" />
          </circle>
        </g>
      )}

      {hintText && (
        <text
          x={x + w / 2 + 8}
          y={labelY + 3}
          className={hintMuted ? 'hover-hint-muted' : 'hover-hint'}
          fill={hintMuted ? '#7f8a99' : outlineColor}
          pointerEvents="none"
          style={{ fontSize: 10 }}
        >
          {hintText}
        </text>
      )}
    </g>
  );
}
