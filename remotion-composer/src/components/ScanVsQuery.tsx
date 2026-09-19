import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Turns "Scan is expensive" into an area you can see.
 *
 * Two identical grids stand side by side. The left one fills top-to-bottom
 * in the warning colour — every cell Scan reads and bills for. The right one
 * lights exactly one cell and then stops. The gap between the two painted
 * areas IS the cost difference; no number has to be read for it to land.
 */

interface ScanVsQueryProps {
  rows?: number;
  cols?: number;
  leftLabel?: string;
  rightLabel?: string;
  leftCaption?: string;
  rightCaption?: string;
  /** Seconds the Scan fill takes to cover the whole grid */
  fillSeconds?: number;
  /** Second at which the Query cell lights up */
  queryHitAt?: number;
  backgroundColor?: string;
  color?: string;
  accentColor?: string;
  mutedColor?: string;
  okColor?: string;
  fontFamily?: string;
}

export const ScanVsQuery: React.FC<ScanVsQueryProps> = ({
  rows = 8,
  cols = 6,
  leftLabel = "Scan",
  rightLabel = "Query",
  leftCaption = "読んだ全件に課金",
  rightCaption = "返した分だけ課金",
  fillSeconds = 3.4,
  queryHitAt = 0.6,
  backgroundColor = "#FAFAFA",
  color = "#1A1A2E",
  accentColor = "#E94560",
  mutedColor = "#D1D5DB",
  okColor = "#0F3460",
  fontFamily = "IBM Plex Sans, Noto Sans CJK JP, sans-serif",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  const total = rows * cols;
  // Fill strictly in reading order so it reads as "scanning", not "sparkling".
  const filledCount = Math.floor(
    interpolate(t, [0.3, 0.3 + fillSeconds], [0, total], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  const gridW = width * 0.27;
  const cellGap = 6;
  const cellW = (gridW - cellGap * (cols - 1)) / cols;
  const cellH = cellW;
  const gridH = rows * cellH + cellGap * (rows - 1);
  // Sit above centre: the burned-in subtitle owns the bottom of the frame,
  // and the per-side captions need clear space beneath the grids.
  const gridTop = height * 0.44 - gridH / 2;
  const leftX = width * 0.5 - gridW - width * 0.06;
  const rightX = width * 0.5 + width * 0.06;

  const queryIndex = Math.floor(total * 0.42);
  const queryLit = t >= queryHitAt;

  const renderGrid = (x: number, isScan: boolean) => (
    <>
      {Array.from({ length: total }).map((_, i) => {
        const r = Math.floor(i / cols);
        const c = i % cols;
        const on = isScan ? i < filledCount : queryLit && i === queryIndex;
        const fill = isScan ? accentColor : okColor;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: x + c * (cellW + cellGap),
              top: gridTop + r * (cellH + cellGap),
              width: cellW,
              height: cellH,
              borderRadius: 3,
              background: on ? fill : "transparent",
              border: `2px solid ${on ? fill : mutedColor}`,
            }}
          />
        );
      })}
    </>
  );

  const labelStyle = (x: number, tone: string): React.CSSProperties => ({
    position: "absolute",
    left: x,
    width: gridW,
    textAlign: "center",
    color: tone,
    fontFamily,
  });

  return (
    <AbsoluteFill style={{ background: backgroundColor }}>
      {renderGrid(leftX, true)}
      {renderGrid(rightX, false)}

      <div style={{ ...labelStyle(leftX, accentColor), top: gridTop - height * 0.1, fontSize: 44, fontWeight: 700 }}>
        {leftLabel}
      </div>
      <div style={{ ...labelStyle(rightX, okColor), top: gridTop - height * 0.1, fontSize: 44, fontWeight: 700 }}>
        {rightLabel}
      </div>

      {/* Captions arrive only once each side has finished making its point. */}
      <div
        style={{
          ...labelStyle(leftX, color),
          top: gridTop + gridH + height * 0.025,
          fontSize: 26,
          opacity: interpolate(t, [0.3 + fillSeconds, 0.3 + fillSeconds + 0.4], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {leftCaption}
      </div>
      <div
        style={{
          ...labelStyle(rightX, color),
          top: gridTop + gridH + height * 0.025,
          fontSize: 26,
          opacity: interpolate(t, [queryHitAt + 0.2, queryHitAt + 0.6], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {rightCaption}
      </div>
    </AbsoluteFill>
  );
};
