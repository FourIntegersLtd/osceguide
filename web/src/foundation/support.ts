/** Where people write when something about their account or a payment goes wrong. */
export const SUPPORT_EMAIL = "hello@osceguide.com";

/**
 * When each compliance document took effect and was last changed: the one
 * place to edit when a document is revised, so no page carries its own date.
 */
export const COMPLIANCE_DATES = {
  terms: { effective: "January 1, 2025", updated: "March 23, 2026" },
  cookies: { updated: "December 31, 2024" },
  referrals: { effective: "January 1, 2025", updated: "September 26, 2026" },
  privacy: { effective: "January 1, 2025", updated: "November 13, 2026" },
  disclaimer: { effective: "January 1, 2025", updated: "April 3, 2025" },
} as const;

/** The "Book a demo" mail link every institutions call to action uses. */
export const DEMO_MAILTO = `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent("OSCE Guide Demo")}`;
