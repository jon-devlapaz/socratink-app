export const X_STEP = 90;
export const Y_STEP = 110;
export const LEFT_PAD = 80;
export const RIGHT_PAD = 220;
export const TOP_PAD = 160;
export const BOTTOM_PAD = 160;

export function computeGeometry(graph) {
  if (!graph) return null;
  const { branches, mainTipX } = graph;

  const lanes = branches.map((b) => b.lane);
  const maxLane = lanes.length ? Math.max(0, ...lanes) : 0;
  const minLane = lanes.length ? Math.min(0, ...lanes) : 0;

  const mainY = TOP_PAD + maxLane * Y_STEP;
  const height = mainY + Math.abs(minLane) * Y_STEP + BOTTOM_PAD;
  
  const branchMaxX = branches.reduce(
    (m, b) => Math.max(m, b.commits.length ? b.commits[b.commits.length - 1].x : b.forkX),
    0,
  );
  const gridW = Math.max(mainTipX, branchMaxX) + 2;
  const width = LEFT_PAD + gridW * X_STEP + RIGHT_PAD;

  const xOf = (gx) => LEFT_PAD + gx * X_STEP;
  const yOf = (lane) => mainY - lane * Y_STEP;

  const mainStart = xOf(0);
  const mainEnd = xOf(mainTipX);

  return {
    mainY,
    height,
    width,
    xOf,
    yOf,
    mainStart,
    mainEnd,
  };
}
