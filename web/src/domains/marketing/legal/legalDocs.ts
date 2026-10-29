import { COMPLIANCE_DATES } from "@/foundation/support";

export type ComplianceDocKey = "privacy" | "terms" | "cookies" | "disclaimer" | "referrals" | "accessibility";

export type ComplianceDoc = {
  key: ComplianceDocKey;
  href: string;
  /** Label on the tab row of the legal pages. */
  tabLabel: string;
  /** Label in the footer's Legal column. */
  footerLabel: string;
};

/** The six documents, in the order of the tab row and the footer. */
export const COMPLIANCE_DOCS: readonly ComplianceDoc[] = [
  { key: "privacy", href: "/compliances/privacy-policy", tabLabel: "Privacy Policy", footerLabel: "Privacy Policy" },
  { key: "terms", href: "/compliances/terms-of-service", tabLabel: "Terms of Service", footerLabel: "Terms of Service" },
  { key: "cookies", href: "/compliances/cookies-policy", tabLabel: "Cookie Policy", footerLabel: "Cookie Policy" },
  { key: "disclaimer", href: "/compliances/legal-disclaimer", tabLabel: "Legal Disclaimer", footerLabel: "Legal Disclaimer" },
  { key: "referrals", href: "/compliances/referrals", tabLabel: "Referral Program", footerLabel: "Referral Policy" },
  { key: "accessibility", href: "/compliances/accessibility", tabLabel: "Accessibility Statement", footerLabel: "Accessibility" },
];

export type ComplianceDates = { effective?: string; updated?: string };

/** The dates for a document; the accessibility statement has none in `COMPLIANCE_DATES`. */
export function complianceDates(key: ComplianceDocKey): ComplianceDates {
  if (key === "accessibility") return {};
  const dates: Record<Exclude<ComplianceDocKey, "accessibility">, ComplianceDates> = {
    privacy: COMPLIANCE_DATES.privacy,
    terms: COMPLIANCE_DATES.terms,
    cookies: COMPLIANCE_DATES.cookies,
    disclaimer: COMPLIANCE_DATES.disclaimer,
    referrals: COMPLIANCE_DATES.referrals,
  };
  return dates[key];
}
