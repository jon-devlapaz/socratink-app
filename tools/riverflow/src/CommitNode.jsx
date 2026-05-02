import React from 'react';
import { commitUrl } from './api.js';

const CI_COLORS = {
  success: '#4dba8a',
  failure: '#e05c6b',
  pending: '#d8a867',
};

export default function CommitNode({
  node,
  cx,
  cy,
  color,
  isHovered,
  pulse = false,
  optimistic = false,
  onHover,
  onContextMenu,
}) {
  const r = node.onMain ? 7 : 5.5;
  const ciColor = node.ci ? CI_COLORS[node.ci] : null;
  return (
    <g
      onMouseEnter={() => onHover?.(node, cx, cy)}
      onMouseLeave={() => onHover?.(null)}
      onClick={(e) => {
        if (e.button !== 0) return;
        if (e.defaultPrevented) return;
        if (node.optimistic || node.sha?.length < 40) return;
        window.open(commitUrl(node.sha), '_blank', 'noopener,noreferrer');
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        onContextMenu?.(node, e);
      }}
      style={{ cursor: 'context-menu', opacity: optimistic ? 0.6 : 1 }}
    >
      <circle cx={cx} cy={cy} r={r + 4} fill="transparent" />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={isHovered ? '#f7ece1' : node.onMain ? '#cac4ce' : color}
        stroke={node.onMain ? '#7a6f9a' : '#4a4264'}
        strokeWidth={1.2}
        className={pulse ? 'tip-pulse' : undefined}
      />
      {ciColor && (
        <circle
          cx={cx + r + 4}
          cy={cy - r - 1}
          r={2.6}
          fill={ciColor}
          stroke="#1f1b31"
          strokeWidth={1}
        />
      )}
      {!isHovered && (
        <text
          x={cx}
          y={cy + (node.lane >= 0 ? 22 : -14)}
          textAnchor="middle"
          className="commit-sha"
        >
          {node.short}
        </text>
      )}
    </g>
  );
}

export function CommitTooltip({ node, cx, cy }) {
  if (!node) return null;
  const headLines = [
    node.short,
    node.message?.split('\n')[0]?.slice(0, 80) || '',
    `${node.author || 'unknown'} · ${node.date ? new Date(node.date).toLocaleString() : ''}`,
  ].filter(Boolean);
  const ciLine = node.ci ? `ci · ${node.ci}` : null;
  const showHint = !node.optimistic;
  const lines = [
    ...headLines,
    ...(ciLine ? [ciLine] : []),
    ...(showHint ? ['click → open on github · right-click → branch'] : []),
  ];
  const w = Math.max(...lines.map((l) => l.length)) * 7 + 24;
  const h = lines.length * 16 + 14 + (showHint ? 4 : 0);
  const tx = cx + 14;
  const ty = cy - h - 10;
  const hintIdx = showHint ? lines.length - 1 : -1;
  const ciIdx = ciLine ? headLines.length : -1;
  return (
    <g pointerEvents="none">
      <rect
        x={tx}
        y={ty}
        width={w}
        height={h}
        rx={8}
        fill="#2a2542"
        stroke="#5a4f7a"
        opacity={0.97}
      />
      {lines.map((l, i) => {
        const isHint = i === hintIdx;
        const isCi = i === ciIdx;
        let className = 'tooltip-body';
        let fill;
        if (i === 0) className = 'tooltip-sha';
        else if (isHint) className = 'tooltip-hint';
        else if (isCi) {
          className = 'tooltip-body';
          fill = CI_COLORS[node.ci];
        }
        return (
          <text
            key={i}
            x={tx + 12}
            y={ty + 18 + i * 16 + (isHint ? 4 : 0)}
            className={className}
            fill={fill}
          >
            {l}
          </text>
        );
      })}
    </g>
  );
}
