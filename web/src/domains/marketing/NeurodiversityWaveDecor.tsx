"use client";

import { brandTokens } from "@/foundation/ui/brandTokens";
import { landingAccentGradientStops, landingAccentPalette } from "./landingAccentPalette";

type TubeRibbonSpec = {
  id: string;
  path: string;
  width: number;
  opacity: number;
  gradient: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
    stops: ReadonlyArray<{ offset: string; color: string }>;
  };
};

const PREMIUM_TUBE_RIBBONS: TubeRibbonSpec[] = [
  {
    id: "nd-tube-primary",
    path: "M40 900 C100 680, 80 460, 260 400 C440 340, 360 180, 520 110 C700 30, 980 70, 1360 35",
    width: 118,
    opacity: 0.62,
    gradient: {
      x1: 40,
      y1: 900,
      x2: 1360,
      y2: 35,
      stops: [
        { offset: "0%", color: landingAccentPalette.orange.stroke },
        { offset: "32%", color: landingAccentPalette.purple.stroke },
        { offset: "62%", color: landingAccentPalette.blue.stroke },
        { offset: "100%", color: landingAccentPalette.green.stroke },
      ],
    },
  },
  {
    id: "nd-tube-secondary",
    path: "M1400 870 C1260 690, 1080 530, 900 490 C720 450, 760 270, 600 185 C440 95, 220 65, 50 40",
    width: 76,
    opacity: 0.52,
    gradient: {
      x1: 1400,
      y1: 870,
      x2: 50,
      y2: 40,
      stops: [
        { offset: "0%", color: landingAccentPalette.blue.stroke },
        { offset: "38%", color: landingAccentPalette.purple.stroke },
        { offset: "72%", color: landingAccentPalette.green.stroke },
        { offset: "100%", color: landingAccentPalette.orange.stroke },
      ],
    },
  },
];

/** Same ribbon geometry as premium — classic brand blues only. */
const CLASSIC_TUBE_RIBBONS: TubeRibbonSpec[] = [
  {
    id: "nd-classic-tube-primary",
    path: "M40 900 C100 680, 80 460, 260 400 C440 340, 360 180, 520 110 C700 30, 980 70, 1360 35",
    width: 118,
    opacity: 0.48,
    gradient: {
      x1: 40,
      y1: 900,
      x2: 1360,
      y2: 35,
      stops: [
        { offset: "0%", color: brandTokens.primarySubtle },
        { offset: "32%", color: brandTokens.primaryLight },
        { offset: "62%", color: brandTokens.primary },
        { offset: "100%", color: brandTokens.primaryHover },
      ],
    },
  },
  {
    id: "nd-classic-tube-secondary",
    path: "M1400 870 C1260 690, 1080 530, 900 490 C720 450, 760 270, 600 185 C440 95, 220 65, 50 40",
    width: 76,
    opacity: 0.4,
    gradient: {
      x1: 1400,
      y1: 870,
      x2: 50,
      y2: 40,
      stops: [
        { offset: "0%", color: brandTokens.primaryLight },
        { offset: "38%", color: brandTokens.primary },
        { offset: "72%", color: brandTokens.primaryHover },
        { offset: "100%", color: brandTokens.primarySubtle },
      ],
    },
  },
];

type DecorTone = "classic" | "premium";

const TUBES_BY_TONE: Record<DecorTone, TubeRibbonSpec[]> = {
  premium: PREMIUM_TUBE_RIBBONS,
  classic: CLASSIC_TUBE_RIBBONS,
};

function TubeRibbon({
  spec,
  flowClassName,
  tone,
  filterId,
}: {
  spec: TubeRibbonSpec;
  flowClassName: string;
  tone: DecorTone;
  filterId: string;
}) {
  const isClassic = tone === "classic";

  return (
    <g opacity={spec.opacity}>
      <path
        d={spec.path}
        stroke={isClassic ? "rgba(37, 99, 235, 0.1)" : "rgba(0,0,0,0.22)"}
        strokeWidth={spec.width + 14}
        strokeLinecap="round"
        strokeLinejoin="round"
        transform="translate(6, 16)"
      />
      <path
        d={spec.path}
        stroke={`url(#${spec.id}-gradient)`}
        strokeWidth={spec.width}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter={`url(#${filterId})`}
      />
      <path
        d={spec.path}
        className={flowClassName}
        stroke="rgba(255,255,255,0.42)"
        strokeWidth={Math.max(3, spec.width * 0.08)}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </g>
  );
}

export type NeurodiversityWaveDecorProps = {
  tone?: DecorTone;
};

export function NeurodiversityWaveDecor({
  tone = "premium",
}: NeurodiversityWaveDecorProps) {
  const tubes = TUBES_BY_TONE[tone];
  const waveClassPrefix =
    tone === "classic"
      ? "landing-neurodiversity-wave-classic"
      : "landing-neurodiversity-wave";
  const filterId =
    tone === "classic" ? "nd-classic-tube-soft-shadow" : "nd-tube-soft-shadow";
  const shadowOpacity = tone === "classic" ? 0.12 : 0.28;

  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <svg
        className="absolute inset-0 h-full w-full scale-[1.15]"
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {tubes.map((tube) => (
            <linearGradient
              key={`${tube.id}-gradient`}
              id={`${tube.id}-gradient`}
              gradientUnits="userSpaceOnUse"
              x1={tube.gradient.x1}
              y1={tube.gradient.y1}
              x2={tube.gradient.x2}
              y2={tube.gradient.y2}
            >
              {tube.gradient.stops.map((stop) => (
                <stop
                  key={`${tube.id}-${stop.offset}`}
                  offset={stop.offset}
                  stopColor={stop.color}
                />
              ))}
            </linearGradient>
          ))}

          {tone === "premium" ? (
            <linearGradient
              id="nd-shared-accent-gradient"
              gradientUnits="userSpaceOnUse"
              x1="0"
              y1="900"
              x2="1440"
              y2="0"
            >
              {landingAccentGradientStops.map((stop) => (
                <stop
                  key={`shared-${stop.offset}`}
                  offset={stop.offset}
                  stopColor={stop.color}
                />
              ))}
            </linearGradient>
          ) : null}

          <filter
            id={filterId}
            x="-30%"
            y="-30%"
            width="160%"
            height="160%"
          >
            <feDropShadow
              dx="0"
              dy="12"
              stdDeviation="16"
              floodColor="#000"
              floodOpacity={shadowOpacity}
            />
          </filter>
        </defs>

        {tubes.map((tube, index) => (
          <TubeRibbon
            key={tube.id}
            spec={tube}
            tone={tone}
            filterId={filterId}
            flowClassName={`landing-features-wave ${waveClassPrefix}-${index + 1}`}
          />
        ))}
      </svg>
    </div>
  );
}
