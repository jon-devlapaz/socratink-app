import React from 'react';

const PR_COLORS = {
  open: '#d8a867',   // amber
  merged: '#4dba8a', // success
  closed: '#7a7387',
};

export default function PRCard({
  pr,
  fromX,
  fromY,
  toX,
  toY,
  isNew = false,
  justMerged = false,
  onClick,
}) {
  const state = pr.merged ? 'merged' : pr.state === 'open' ? 'open' : 'closed';
  const color = PR_COLORS[state];

  const cx = (fromX + toX) / 2;
  const cy = fromY * 0.35;
  const path = `M ${fromX} ${fromY} Q ${cx} ${cy} ${toX} ${toY}`;

  // For draw-on we override the dasharray to one long dash sized to the path.
  // 1200 is comfortably greater than any plausible Bezier we'll draw at our zoom.
  const drawOnLength = 1200;

  const interactive = state === 'open' && !pr.merged;
  return (
    <g
      onClick={interactive ? (e) => onClick?.(pr, e) : undefined}
      style={{
        cursor: interactive ? 'pointer' : 'default',
        opacity: pr.optimistic ? 0.6 : 1,
      }}
    >
      {/* Underlying styled arc */}
      <path
        d={path}
        stroke={color}
        strokeWidth={state === 'merged' ? 3 : 2.5}
        fill="none"
        opacity={state === 'closed' ? 0.4 : 0.9}
        strokeDasharray={state === 'open' ? '6 4' : 'none'}
        className={state === 'open' ? 'pr-arc-flow' : ''}
        style={{ transition: 'stroke 400ms ease, stroke-width 400ms ease' }}
      />
      {/* One-shot draw-on overlay; mounted only when this PR is newly observed */}
      {isNew && (
        <path
          d={path}
          stroke={color}
          strokeWidth={state === 'merged' ? 3 : 2.5}
          fill="none"
          strokeDasharray={drawOnLength}
          strokeDashoffset={drawOnLength}
          className="pr-arc-drawon"
        />
      )}
      {/* Merge ripple at the confluence point */}
      {justMerged && (
        <g pointerEvents="none">
          <circle
            cx={toX}
            cy={toY}
            r={0}
            fill="none"
            stroke={PR_COLORS.merged}
            strokeWidth={2}
            opacity={0.9}
          >
            <animate
              attributeName="r"
              from="0"
              to="56"
              dur="0.8s"
              fill="freeze"
            />
            <animate
              attributeName="opacity"
              from="0.9"
              to="0"
              dur="0.8s"
              fill="freeze"
            />
          </circle>
          <circle
            cx={toX}
            cy={toY}
            r={0}
            fill={PR_COLORS.merged}
            opacity={0.5}
          >
            <animate
              attributeName="r"
              from="0"
              to="14"
              dur="0.4s"
              fill="freeze"
            />
            <animate
              attributeName="opacity"
              from="0.6"
              to="0"
              dur="0.8s"
              fill="freeze"
            />
          </circle>
        </g>
      )}
      {state === 'open' && (
        <PRFloatingCard
          pr={pr}
          x={cx}
          y={cy - 24}
          color={color}
        />
      )}
    </g>
  );
}

function PRFloatingCard({ pr, x, y, color }) {
  const title = pr.title.length > 42 ? pr.title.slice(0, 40) + '…' : pr.title;
  const w = Math.max(title.length * 7 + 60, 200);
  const h = 36;
  const numText = pr.number > 0 ? `#${pr.number}` : '#…';
  return (
    <g>
      <rect
        x={x - w / 2}
        y={y - h}
        width={w}
        height={h}
        rx={8}
        fill="#2a2542"
        stroke={color}
        strokeWidth={1.2}
      />
      <text x={x - w / 2 + 12} y={y - h + 15} className="pr-num" fill={color}>
        {numText}
      </text>
      <text x={x - w / 2 + 44} y={y - h + 15} className="pr-title">
        {title}
      </text>
      <text x={x - w / 2 + 12} y={y - 8} className="pr-meta">
        open · merge clean
      </text>
    </g>
  );
}
