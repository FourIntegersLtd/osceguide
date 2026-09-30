/**
 * Section surfaces for the marketing pages (`/`, the SCA/PLAB/Ortho exam
 * landings, and institutions).
 *
 * All of them render on the shared sky canvas. A surface marks a section as
 * part of the page rhythm: fading hairline divider plus a sky / ice / azure
 * wash. Details live in globals.css under `.landing-section-*`, scoped to
 * `[data-b2c-landing-surface="cream"]`.
 */
export const landingSectionSurfaces = {
  /** No wash of its own — opts a section into the shared divider rhythm. */
  plain: "landing-section-surface",
  /** First-fold sky radial — no top divider. */
  hero: "landing-section-hero",
  numbers: "landing-section-surface landing-section-numbers",
  features: "landing-section-surface landing-section-features",
  exams: "landing-section-surface landing-section-exams",
  practice: "landing-section-surface landing-section-practice",
  neuro: "landing-section-surface landing-section-neuro",
  founders: "landing-section-surface landing-section-founders",
  faq: "landing-section-surface landing-section-faq",
  pricing: "landing-section-surface landing-section-pricing",
  feedback: "landing-section-surface landing-section-feedback",
  testimonials: "landing-section-surface landing-section-testimonials",
  blog: "landing-section-surface landing-section-blog",
  footer: "landing-section-surface landing-section-footer",
} as const;

export type LandingSectionSurfaceKey = keyof typeof landingSectionSurfaces;
