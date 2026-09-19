import { getButtonClassName } from "@/foundation/ui";
import type { LandingThemeVariant } from "./landingTheme";
import { landingAccent, landingFocusRing } from "./landingTheme";

export type LandingTypographyVariant = LandingThemeVariant;

/**
 * Heading weight, radii, borders, and shadows resolve through `landing-*`
 * CSS variables. Their fallbacks are the pre-sky values, so only the
 * sky surface (`[data-b2c-landing-surface="cream"]`) picks up the new look.
 */
const headingWeight = "font-[number:var(--landing-heading-weight,600)]";
const heroWeight = "font-[number:var(--landing-hero-weight,600)]";

export function createLandingType(_variant: LandingTypographyVariant) {
  // Exam and classic landings now share one palette and scale; the parameter
  // stays so callers keep declaring their variant for when they diverge again.
  const textList = "text-landing-ink-body";
  const textDarkMuted = "text-b2c-text-muted";
  const card = "rounded-landing-card border border-landing-warm bg-landing-card-muted shadow-landing-card hover:shadow-landing-card-hover";

  return {
    eyebrow:
      "font-landing-mono text-[10px] font-medium uppercase tracking-[0.13em] text-[color:var(--landing-eyebrow,var(--b2c-text-muted))]",
    sectionTitle:
      `font-landing-heading text-[clamp(1.625rem,3.2vw,2.25rem)] ${headingWeight} leading-[1.15] tracking-[-0.025em] text-osce-ink-900`,
    sectionSubtitle:
      "font-landing-body mt-[var(--landing-subtitle-gap,0.875rem)] text-[length:var(--landing-subtitle-size,1rem)] leading-relaxed text-landing-ink-muted",
    sectionSubtitleCentered:
      "font-landing-body mx-auto mt-[var(--landing-subtitle-gap,0.875rem)] max-w-3xl text-[length:var(--landing-subtitle-size,1rem)] leading-relaxed text-landing-ink-muted",
    itemTitle:
      "font-landing-heading text-[17px] font-semibold leading-[1.3] tracking-[-0.02em] text-osce-ink-900 sm:text-lg",
    itemBody: "font-landing-body text-sm leading-relaxed text-b2c-text-secondary sm:text-[14.5px] sm:leading-[1.6]",
    heroTitle:
      `font-landing-heading text-[clamp(2.375rem,5.6vw,4rem)] ${heroWeight} leading-[1.06] tracking-[-0.03em] text-osce-ink-900`,
    heroMainTitle:
      `font-landing-heading text-[clamp(2.375rem,5.6vw,4rem)] ${heroWeight} leading-[1.06] tracking-[-0.03em] text-osce-ink-900`,
    heroMainSubhead:
      "font-landing-body mt-6 max-w-2xl text-lg leading-relaxed text-b2c-text-secondary sm:mt-8",
    heroTitleExam:
      `font-landing-heading mx-auto max-w-5xl text-center text-4xl ${heroWeight} leading-tight tracking-tight text-osce-ink-900 sm:text-5xl lg:mx-0 lg:max-w-none lg:text-left lg:text-6xl`,
    heroLead:
      "font-landing-body mt-4 text-base leading-relaxed text-b2c-text-secondary md:mt-6 md:text-lg",
    heroLeadExam:
      "font-landing-body mt-4 max-w-3xl text-center text-lg leading-relaxed text-landing-ink-muted md:mt-6 md:text-xl lg:mx-0 lg:max-w-2xl lg:text-left",
    linkAction:
      "font-landing-body text-sm font-medium text-osce-accent transition-colors hover:text-osce-accent-hover",
    faqQuestion:
      "font-landing-body text-base font-medium leading-snug text-osce-ink-900",
    faqAnswer:
      "font-landing-body text-[15px] leading-[1.65] text-landing-ink-muted",
    /** Two tiers only, identical on classic and exam pages. */
    sectionPadding: "py-20 md:py-24",
    sectionPaddingCompact: "py-16 sm:py-20",
    /**
     * One section width across `/` and the exam landings, matching the
     * 1200px page cap the app uses. Exam pages previously used Tailwind's
     * uncustomised `container`, which runs to 1536px at 2xl, so the two
     * marketing surfaces disagreed on measure — and the footer, which hard
     * coded 1200px, was narrower than the body above it on exam pages.
     */
    sectionShell: "mx-auto w-full max-w-osce-page px-5 sm:px-7",
    featureCard: `${card} p-6 transition-[color,background-color,border-color,box-shadow] hover:border-osce-accent-subtle sm:p-6`,
    featureCardMuted: `${card} p-6 transition-[color,background-color,border-color,box-shadow] hover:border-osce-accent-subtle sm:p-6`,
    listItem: `font-landing-body flex items-start gap-3 text-sm font-medium ${textList}`,
    quoteBody:
      "font-landing-heading text-xl font-normal leading-snug text-[#F9FAFB] md:text-2xl",
    quoteAttribution:
      "font-landing-body text-xs font-semibold uppercase tracking-[0.14em] text-osce-accent-subtle",
    darkSectionTitle:
      "font-landing-heading text-3xl font-bold tracking-tight text-white md:text-4xl",
    darkSectionSubtitle: `font-landing-body mt-4 leading-relaxed ${textDarkMuted}`,
    darkItemTitle: "font-landing-heading text-lg font-semibold text-white",
    darkItemBody: `font-landing-body leading-relaxed ${textDarkMuted}`,
    navLink:
      "font-landing-body text-sm text-landing-ink-body transition-colors hover:text-osce-ink-900",
    navContact:
      "font-landing-body text-sm font-medium text-landing-ink-body transition-colors hover:text-osce-ink-900",
    navCtaPrimary: getButtonClassName({
      variant: "primary",
      size: "md",
      className: `group w-full gap-2 sm:w-auto ${landingAccent.btn}`,
    }),
    navCtaSecondary: getButtonClassName({
      variant: "outline",
      size: "md",
      className: "w-full sm:w-auto",
    }),
    ctaPrimary: getButtonClassName({
      variant: "primary",
      size: "hero",
      className: `group sm:w-auto ${landingAccent.btn}`,
    }),
    ctaSecondary: `inline-flex items-center justify-center rounded-md border border-landing-warm-strong bg-[color:var(--landing-cta-secondary-bg,#ffffff)] px-5 py-2.5 font-landing-body text-sm font-medium text-[color:var(--landing-cta-secondary-ink,var(--b2c-text-primary))] shadow-landing-cta-secondary transition-colors hover:border-osce-accent hover:text-osce-accent sm:w-auto ${landingFocusRing}`,
    ctaInk: `inline-flex items-center justify-center gap-2 rounded-md bg-osce-accent px-5 py-2.5 font-landing-body text-sm font-medium text-white shadow-landing-cta transition-colors hover:bg-osce-accent-hover ${landingFocusRing}`,
  };
}

export type LandingType = ReturnType<typeof createLandingType>;

/** Exam landings (SCA, PLAB, Ortho) and fallback when no LandingVariantProvider. */
export const landingType = createLandingType("exam");

/** @deprecated Use createLandingType("classic") or useLandingVariant().type */
export const baseLandingType = createLandingType("classic");
