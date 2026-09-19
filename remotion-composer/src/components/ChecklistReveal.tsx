import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

/**
 * The closing beat: one instruction, written out by hand, then ticked.
 *
 * The line reveals left-to-right as if being written, and the checkbox is
 * drawn with an SVG path — the playbook's `entrance: draw-in` taken literally.
 * Only one item, because the video asks the viewer to remember exactly one
 * thing.
 */

interface ChecklistRevealProps {
  heading?: string;
  items?: string[];
  /** Seconds each line takes to write itself */
  writeSeconds?: number;
  /** Delay before the tick is drawn, after the line finishes */
  checkDelaySeconds?: number;
  backgroundColor?: string;
  color?: string;
  accentColor?: string;
  mutedColor?: string;
  fontFamily?: string;
}

export const ChecklistReveal: React.FC<ChecklistRevealProps> = ({
  heading = "テーブルを作る前に",
  items = ["アクセスパターンを、箇条書きで全部書き出す"],
  writeSeconds = 1.2,
  checkDelaySeconds = 0.3,
  backgroundColor = "#FAFAFA",
  color = "#1A1A2E",
  accentColor = "#E94560",
  mutedColor = "#6B7280",
  fontFamily = "IBM Plex Sans, Noto Sans CJK JP, sans-serif",
}) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const t = frame / fps;

  const headingOpacity = interpolate(t, [0.1, 0.6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const boxSize = 46;

  return (
    <AbsoluteFill
      style={{
        background: backgroundColor,
        fontFamily,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div style={{ width: width * 0.66 }}>
        <div
          style={{
            fontSize: 34,
            color: mutedColor,
            marginBottom: 34,
            opacity: headingOpacity,
            transform: `translateY(${interpolate(headingOpacity, [0, 1], [14, 0])}px)`,
          }}
        >
          {heading}
        </div>

        {items.map((item, i) => {
          const start = 0.7 + i * (writeSeconds + checkDelaySeconds + 0.4);
          // The clip rectangle is what makes it read as "being written"
          // rather than "fading in".
          const written = interpolate(t, [start, start + writeSeconds], [0, 100], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const checkStart = start + writeSeconds + checkDelaySeconds;
          const checkProgress = interpolate(t, [checkStart, checkStart + 0.45], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });
          const boxVisible = t >= start;

          return (
            <div
              key={item}
              style={{ display: "flex", alignItems: "center", gap: 26, marginBottom: 26 }}
            >
              <svg width={boxSize} height={boxSize} style={{ flexShrink: 0 }}>
                <rect
                  x={2}
                  y={2}
                  width={boxSize - 4}
                  height={boxSize - 4}
                  rx={7}
                  fill="none"
                  stroke={boxVisible ? color : "transparent"}
                  strokeWidth={3}
                />
                {/* strokeDashoffset drives the tick being drawn stroke-first */}
                <path
                  d={`M ${boxSize * 0.24} ${boxSize * 0.52} L ${boxSize * 0.43} ${boxSize * 0.71} L ${boxSize * 0.77} ${boxSize * 0.29}`}
                  fill="none"
                  stroke={accentColor}
                  strokeWidth={5}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray={60}
                  strokeDashoffset={60 - 60 * checkProgress}
                />
              </svg>

              <div
                style={{
                  fontSize: 42,
                  color,
                  lineHeight: 1.7,
                  clipPath: `inset(0 ${100 - written}% 0 0)`,
                  whiteSpace: "nowrap",
                }}
              >
                {item}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
