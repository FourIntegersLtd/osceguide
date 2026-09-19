/**
 * Cohesive vibrant icon surfaces for landing pages.
 * Solid fills with white glyphs — matches the feature-card treatment.
 */
export const landingIconPalette = {
  cyan: "#13B5EA",
  green: "#2CA01C",
  indigo: "#6366F1",
  blue: "#2563EB",
  violet: "#7C3AED",
  orange: "#F97316",
  rose: "#E11D48",
  teal: "#0D9488",
  amber: "#D97706",
} as const;

export type LandingIconColor = keyof typeof landingIconPalette;

export function landingIconSurface(color: LandingIconColor): string {
  return `bg-[${landingIconPalette[color]}]`;
}
