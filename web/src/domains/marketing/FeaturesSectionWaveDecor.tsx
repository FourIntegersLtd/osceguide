"use client";

import { landingAccentPalette } from "./landingAccentPalette";

const FEATURE_WAVES: Array<{
  className: string;
  path: string;
  strokeWidth: number;
  accent: keyof typeof landingAccentPalette;
}> = [
  {
    className: "landing-features-wave landing-features-wave-1",
    path: "M-80 150 C360 400, 1080 400, 1520 150",
    strokeWidth: 2,
    accent: "blue",
  },
  {
    className: "landing-features-wave landing-features-wave-2",
    path: "M60 220 C-10 520, 140 760, 460 920",
    strokeWidth: 1.75,
    accent: "purple",
  },
  {
    className: "landing-features-wave landing-features-wave-3",
    path: "M1420 760 C1500 480, 1360 220, 960 50",
    strokeWidth: 1.75,
    accent: "green",
  },
  {
    className: "landing-features-wave landing-features-wave-4",
    path: "M-60 840 C480 620, 960 620, 1500 840",
    strokeWidth: 2.25,
    accent: "orange",
  },
  {
    className: "landing-features-wave landing-features-wave-5",
    path: "M160 580 C520 420, 920 420, 1280 580",
    strokeWidth: 1.5,
    accent: "purple",
  },
];

/**
 * Semi-circular arc waves for “Your Complete OSCE Solution”.
 * Stroke colors match the community stats accent palette.
 */
export function FeaturesSectionWaveDecor() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
      <svg
        className="absolute inset-0 h-full w-full"
        viewBox="0 0 1440 900"
        preserveAspectRatio="none"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {FEATURE_WAVES.map((wave) => (
          <path
            key={wave.className}
            className={wave.className}
            d={wave.path}
            stroke={landingAccentPalette[wave.accent].stroke}
            strokeWidth={wave.strokeWidth}
            strokeLinecap="round"
          />
        ))}
      </svg>
    </div>
  );
}
