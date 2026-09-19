import { brandTokens } from "@/foundation/ui/brandTokens";

/**
 * Decorative accent palette for NewBaseLandingPage only (waves, premium stats).
 * Base landing (`/`) does not use these accents.
 */
export const landingAccentPalette = {
  blue: {
    iconBg: "bg-osce-accent-muted",
    iconText: "text-osce-accent",
    valueText: "text-osce-accent",
    iconRing: "ring-osce-accent/25",
    stroke: brandTokens.primary,
  },
  purple: {
    iconBg: "bg-violet-100",
    iconText: "text-violet-600",
    valueText: "text-violet-700",
    iconRing: "ring-violet-300/60",
    stroke: "#7c3aed",
  },
  green: {
    iconBg: "bg-emerald-100",
    iconText: "text-emerald-600",
    valueText: "text-emerald-700",
    iconRing: "ring-emerald-300/60",
    stroke: "#059669",
  },
  orange: {
    iconBg: "bg-orange-100",
    iconText: "text-orange-500",
    valueText: "text-orange-600",
    iconRing: "ring-orange-300/60",
    stroke: "#ea580c",
  },
  teal: {
    iconBg: "bg-teal-100",
    iconText: "text-teal-600",
    valueText: "text-teal-700",
    iconRing: "ring-teal-300/60",
    stroke: "#0d9488",
  },
} as const;

export type LandingAccentKey = keyof typeof landingAccentPalette;

/** Gradient stops for ribbon / wave SVG fills using the same palette. */
export const landingAccentGradientStops = [
  { offset: "0%", color: landingAccentPalette.blue.stroke },
  { offset: "34%", color: landingAccentPalette.purple.stroke },
  { offset: "67%", color: landingAccentPalette.green.stroke },
  { offset: "100%", color: landingAccentPalette.orange.stroke },
] as const;
