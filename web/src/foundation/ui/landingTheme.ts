import { brandTokens } from "@/foundation/ui/brandTokens";

export type LandingThemeVariant = "classic" | "exam";

/**
 * Section/card surface palette.
 * `cream` is the sky-blue canvas on `/` (and exam / institutions marketing).
 * `legacy` is reserved for the earlier grey/blue opt-out.
 */
export type LandingSurfaceVariant = "cream" | "legacy";

export const landingCssVariables = {
  "--brand-primary": brandTokens.primary,
  "--brand-primary-hover": brandTokens.primaryHover,
  "--brand-primary-muted": brandTokens.primaryMuted,
  "--brand-primary-subtle": brandTokens.primarySubtle,
  "--brand-primary-light": brandTokens.primaryLight,
  "--b2c-primary": brandTokens.primary,
  "--b2c-primary-hover": brandTokens.primaryHover,
  "--b2c-primary-muted": brandTokens.primaryMuted,
  "--b2c-primary-subtle": brandTokens.primarySubtle,
  "--b2c-primary-light": brandTokens.primaryLight,
} as const;

/** Shared focus ring for landing CTAs, cards, and disclosure triggers. */
export const landingFocusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 focus-visible:ring-offset-landing-canvas";

export const landingAccent = {
  btn: `!bg-osce-accent hover:!bg-osce-accent-hover ${landingFocusRing}`,
  btnInk:
    "bg-osce-accent text-white hover:bg-osce-accent-hover focus-visible:ring-2 focus-visible:ring-osce-accent-subtle focus-visible:ring-offset-2",
  text: "text-osce-accent",
  textHover: "hover:text-osce-accent-hover",
  bgMuted: "bg-osce-accent-muted",
  bgSubtle: "bg-osce-accent-subtle",
  borderSubtle: "border-osce-accent-subtle",
  icon: "text-osce-accent",
  iconHoverBg: "group-hover:bg-osce-accent-hover",
  gradient: "from-osce-accent to-osce-accent-hover",
} as const;

export type LandingAccent = typeof landingAccent;

export const landingEmphasisGradientClassName =
  "bg-gradient-to-br from-osce-accent via-osce-accent-hover to-[#1e3a5f]";

export type LandingTheme = {
  rootProps: {
    "data-b2c-landing-variant": LandingThemeVariant;
    "data-b2c-landing-surface": LandingSurfaceVariant;
    className: string;
  };
  navClassName: string;
  accent: LandingAccent;
  emphasisGradientClassName: string;
};

/**
 * One nav treatment for every marketing page. The exam landings used `fixed`,
 * which took the 60px header out of flow while their hero kept the same
 * `pt-14 sm:pt-16` as `/` — so the top of the exam hero sat under the nav.
 */
const landingNavClassName =
  "sticky top-0 z-50 border-b border-landing-divider bg-landing-nav backdrop-blur-[10px]";

const classicTheme: LandingTheme = {
  rootProps: {
    "data-b2c-landing-variant": "classic",
    "data-b2c-landing-surface": "cream",
    className: "min-h-screen overflow-x-clip bg-landing-canvas text-osce-ink-900",
  },
  navClassName: landingNavClassName,
  accent: landingAccent,
  emphasisGradientClassName: `bg-gradient-to-r ${landingAccent.gradient}`,
};

const examTheme: LandingTheme = {
  rootProps: {
    "data-b2c-landing-variant": "exam",
    "data-b2c-landing-surface": "cream",
    className: "min-h-screen overflow-x-clip bg-landing-canvas text-osce-ink-900",
  },
  navClassName: landingNavClassName,
  accent: landingAccent,
  emphasisGradientClassName: `bg-gradient-to-r ${landingAccent.gradient}`,
};

export function getLandingTheme(variant: LandingThemeVariant): LandingTheme {
  return variant === "exam" ? examTheme : classicTheme;
}

/** @deprecated Use getLandingTheme("classic").accent */
export const baseLandingBlue = landingAccent;

/** @deprecated Use getLandingTheme("classic").rootProps */
export const baseLandingRootProps = classicTheme.rootProps;
