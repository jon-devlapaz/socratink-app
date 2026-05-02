import React, { useState } from 'react';

export const PR_COLORS = {
  open: '#d8a867',   // amber — drilled state
  merged: '#4dba8a', // success
  closed: '#7a7387',
};

export default function AtMainPin({
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
          className="hover-hint"
          fill={outlineColor}
          pointerEvents="none"
          style={{ fontSize: 10 }}
        >
          {hintText}
        </text>
      )}
    </g>
  );
}
