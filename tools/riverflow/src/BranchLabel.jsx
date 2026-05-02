import React, { useState } from 'react';

export default function BranchLabel({ branch, x, y, openPR, onClick }) {
  const [hover, setHover] = useState(false);
  const interactive = !openPR;
  const above = branch.lane > 0;
  const labelY = above ? y - 26 : y + 32;
  const w = Math.max(branch.name.length * 7 + 24, 70);
  const h = 22;

  let hintText = null;
  let hintMuted = false;
  if (hover) {
    if (interactive) {
      hintText = 'open PR →';
    } else if (openPR && openPR.number > 0) {
      hintText = `PR #${openPR.number} open`;
      hintMuted = true;
    } else if (openPR) {
      hintText = 'PR open';
      hintMuted = true;
    }
  }

  return (
    <g
      onClick={interactive ? (e) => onClick?.(branch, e) : undefined}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ cursor: interactive ? 'pointer' : 'default' }}
    >
      <line
        x1={x}
        y1={y}
        x2={x}
        y2={labelY + (above ? h / 2 : -h / 2)}
        stroke={branch.color}
        strokeWidth={1}
        opacity={0.6}
      />
      <rect
        x={x - w / 2}
        y={labelY - h / 2}
        width={w}
        height={h}
        rx={8}
        fill="#2a2542"
        stroke={branch.color}
        strokeWidth={1.2}
      />
      <text
        x={x}
        y={labelY + 4}
        textAnchor="middle"
        className="branch-label"
        fill={branch.color}
      >
        {branch.name}
      </text>
      <text
        x={x}
        y={labelY + h / 2 + 12}
        textAnchor="middle"
        className="branch-meta"
      >
        +{branch.ahead} / -{branch.behind}
      </text>
      {hintText && (
        <text
          x={x + w / 2 + 8}
          y={labelY + 4}
          className={hintMuted ? 'hover-hint-muted' : 'hover-hint'}
          fill={hintMuted ? '#7f8a99' : branch.color}
          pointerEvents="none"
        >
          {hintText}
        </text>
      )}
    </g>
  );
}
