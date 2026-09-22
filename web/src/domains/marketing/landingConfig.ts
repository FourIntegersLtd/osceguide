export type LandingSectionKey =
  | "hero"
  | "numbers"
  | "features"
  | "exams"
  | "practice"
  | "neuro"
  | "founders"
  | "faq"
  | "pricing"
  | "feedback"
  | "testimonials"
  | "footer";

/*
 * Ordered as a subscribing doctor's questions arrive: what is this, does it
 * work, what do I get, does it cover my exam, do people like me vouch for it —
 * then the price, then remaining objections.
 *
 * `feedback` is the "Help Us Improve" form, not product feedback: it asks
 * something of the visitor rather than offering anything, so it sits last.
 */
export const landingSections: readonly LandingSectionKey[] = [
  "hero",
  "numbers",
  "features",
  "exams",
  "practice",
  "neuro",
  "founders",
  "testimonials",
  "pricing",
  "faq",
  "feedback",
  "footer",
];

export type LandingNavLink = {
  href: string;
  label: string;
  external?: boolean;
};

export type LandingNavConfig = {
  desktopLinks: LandingNavLink[];
  mobileLinks: LandingNavLink[];
  mobileCtaLabel: string;
};

export const landingNavConfig: LandingNavConfig = {
  desktopLinks: [
    { href: "#feedback", label: "Feedback" },
    { href: "#exams", label: "Exams" },
    { href: "#pricing", label: "Pricing" },
    { href: "#faq", label: "FAQ" },
  ],
  mobileLinks: [
    { href: "#feedback", label: "Feedback" },
    { href: "#exams", label: "Exams" },
    { href: "#pricing", label: "Pricing" },
    { href: "#faq", label: "FAQ" },
    { href: "/institutions", label: "Institutions" },
  ],
  mobileCtaLabel: "Login",
};
