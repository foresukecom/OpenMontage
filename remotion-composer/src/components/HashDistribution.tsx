import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * Explains "the key IS the location" — the single idea that makes DynamoDB's
 * query restrictions make sense.
 *
 * Keys fly in from the left, pass through a hash() block that flashes, then
 * land in one of several partition boxes. Each key lands in a different box,
 * so the distribution reads as deliberate rather than random. Later keys move
 * faster than earlier ones: the first pass teaches the mechanism, the rest
 * show it is routine.
 */

export interface HashKey {
  /** Key text, e.g. "user#1234" */
  label: string;
  /** Which partition box (0-indexed) this key hashes into */
  target: number;
}

interface HashDistributionProps {
  keys?: HashKey[];
  partitionCount?: number;
  partitionLabelPrefix?: string;
  hashLabel?: string;
  backgroundColor?: string;
  color?: string;
  accentColor?: string;
  mutedColor?: string;
  fontFamily?: string;
  /**
   * Text colour for the key chips. Kept separate from `backgroundColor`
   * because callers legitimately pass "transparent" there to let a themed
   * backdrop show through — deriving chip text from it made the label vanish.
   */
  keyTextColor?: string;
  /** Seconds each key takes to travel, first key slowest */
  travelSeconds?: number[];
}

export const HashDistribution: React.FC<HashDistributionProps> = ({
  keys = [
    { label: "user#1234", target: 2 },
    { label: "user#5678", target: 0 },
    { label: "order#42", target: 3 },
  ],
  partitionCount = 4,
  partitionLabelPrefix = "パーティション",
  hashLabel = "hash()",
  backgroundColor = "#FAFAFA",
  color = "#1A1A2E",
  accentColor = "#E94560",
  mutedColor = "#6B7280",
  fontFamily = "IBM Plex Sans, Noto Sans CJK JP, sans-serif",
  keyTextColor = "#FFFFFF",
  travelSeconds = [3.2, 2.4, 2.0],
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;

  // Lay the stage out in thirds: key column, hash block, partition column.
  const keyX = width * 0.16;
  const hashX = width * 0.44;
  const boxX = width * 0.74;
  const boxW = width * 0.2;
  const boxH = height * 0.13;
  const boxGap = height * 0.035;
  const stackH = partitionCount * boxH + (partitionCount - 1) * boxGap;
  const boxTop = (height - stackH) / 2;

  const boxCenterY = (i: number) => boxTop + i * (boxH + boxGap) + boxH / 2;

  // Each key starts once the previous one has landed.
  const starts: number[] = [];
  let acc = 0.4;
  keys.forEach((_, i) => {
    starts.push(acc);
    acc += (travelSeconds[i] ?? 2.0) + 0.25;
  });

  return (
    <AbsoluteFill style={{ background: backgroundColor, fontFamily }}>
      {/* hash() block */}
      <div
        style={{
          position: "absolute",
          left: hashX - width * 0.06,
          top: height / 2 - height * 0.06,
          width: width * 0.12,
          height: height * 0.12,
          border: `3px solid ${color}`,
          borderRadius: 10,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 34,
          fontWeight: 600,
          color,
          // "transparent" here is intentional when the theme paints the
          // backdrop — the block reads as an outline on the paper texture.
          background: backgroundColor,
          // Flash white-hot the moment a key passes through.
          boxShadow: keys.reduce((glow, _, i) => {
            const s = starts[i];
            const dur = travelSeconds[i] ?? 2.0;
            const mid = s + dur * 0.45;
            const near = Math.abs(t - mid) < 0.18 ? 1 : 0;
            return Math.max(glow, near);
          }, 0)
            ? `0 0 46px ${accentColor}`
            : "none",
        }}
      >
        {hashLabel}
      </div>

      {/* Partition boxes */}
      {Array.from({ length: partitionCount }).map((_, i) => {
        // A box lights up briefly as its key lands, then settles to "filled".
        const landedBy = keys.findIndex((k, ki) => {
          const s = starts[ki];
          const dur = travelSeconds[ki] ?? 2.0;
          return k.target === i && t >= s + dur;
        });
        const justLanded = keys.some((k, ki) => {
          const s = starts[ki];
          const dur = travelSeconds[ki] ?? 2.0;
          return k.target === i && t >= s + dur && t < s + dur + 0.35;
        });
        const filled = landedBy >= 0;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: boxX,
              top: boxTop + i * (boxH + boxGap),
              width: boxW,
              height: boxH,
              border: `3px solid ${filled ? accentColor : mutedColor}`,
              borderRadius: 10,
              background: filled ? `${accentColor}18` : "transparent",
              transform: `scale(${justLanded ? 1.05 : 1})`,
              transition: "none",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              color: filled ? accentColor : mutedColor,
              fontWeight: filled ? 600 : 400,
            }}
          >
            {partitionLabelPrefix}
            {i + 1}
          </div>
        );
      })}

      {/* Keys in flight */}
      {keys.map((k, i) => {
        const s = starts[i];
        const dur = travelSeconds[i] ?? 2.0;
        if (t < s) return null;

        const p = Math.min((t - s) / dur, 1);
        const targetY = boxCenterY(k.target);
        const startY = height / 2;

        // Travel in two legs so the hash block is visibly the turning point:
        // straight to hash(), then angled down/up into the chosen box.
        const x =
          p < 0.45
            ? interpolate(p, [0, 0.45], [keyX, hashX])
            : interpolate(p, [0.45, 1], [hashX, boxX - 14]);
        const y =
          p < 0.45 ? startY : interpolate(p, [0.45, 1], [startY, targetY]);

        // Fade out just as it enters the box — the box lighting up carries on.
        const opacity = p > 0.94 ? interpolate(p, [0.94, 1], [1, 0]) : 1;

        return (
          <div
            key={k.label}
            style={{
              position: "absolute",
              left: x,
              top: y,
              transform: "translate(-50%, -50%)",
              opacity,
              padding: "10px 18px",
              borderRadius: 8,
              background: color,
              color: keyTextColor,
              fontSize: 26,
              fontWeight: 500,
              whiteSpace: "nowrap",
            }}
          >
            {k.label}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
