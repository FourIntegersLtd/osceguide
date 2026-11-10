import { SUPPORT_EMAIL } from "@/foundation/support";
import { VISIBLE_EXAMS, type ExamName } from "@/domains/marketing/pricingContent";
import { COMPLIANCE_DOCS } from "@/domains/marketing/legal/legalDocs";

export type SiteLink = { href: string; label: string };

const LANDING_ANCHORS = [
  { id: "features", label: "Features" },
  { id: "exams", label: "Exams" },
  { id: "pricing", label: "Pricing" },
  { id: "faq", label: "FAQ" },
] as const;

type AnchorId = (typeof LANDING_ANCHORS)[number]["id"];

/** Links to sections of the landing; `prefix` is "" on the landing itself and "/" elsewhere. */
function anchors(prefix: "" | "/", ids: readonly AnchorId[]): readonly SiteLink[] {
  return ids.map((id) => ({ href: `${prefix}#${id}`, label: LANDING_ANCHORS.find((a) => a.id === id)!.label }));
}

/** Centre links of the nav. On the landing they are anchors on the same page. */
export const LANDING_NAV_LINKS = anchors("", ["features", "exams", "pricing", "faq"]);

export const SITE_NAV_LINKS: readonly SiteLink[] = [
  { href: "/blogs", label: "Blogs" },
  ...anchors("/", ["exams", "pricing"]),
  { href: "/institutions", label: "Institutions" },
];

export const FOOTER_PRODUCT: readonly SiteLink[] = [...anchors("/", ["features", "pricing", "faq"]), { href: "/feedback", label: "Feedback" }];

export const FOOTER_COMPANY: readonly SiteLink[] = [
  { href: "/institutions", label: "For universities and programmes" },
  { href: "/login", label: "Log in" },
  { href: `mailto:${SUPPORT_EMAIL}`, label: "Contact us" },
  { href: "/compliances/accessibility", label: "Accessibility" },
];

/** Exam landings; `sca.osceguide.com` rewrites to the same pages. */
export const EXAM_LINKS: readonly (SiteLink & { exam: ExamName })[] = [
  { exam: "SCA", href: "/exams/sca", label: "SCA (UK)" },
  { exam: "PLAB", href: "/exams/plab", label: "PLAB 2 (UK)" },
  { exam: "CASC", href: "/exams/casc", label: "MRCPsych CASC" },
  { exam: "ORTHO", href: "/exams/ortho", label: "Orthopaedic ST3" },
];

/** Limited to `VISIBLE_EXAMS`: a hidden exam's page stays reachable but is linked from nowhere. */
export const FOOTER_EXAMS: readonly SiteLink[] = EXAM_LINKS.filter((l) => VISIBLE_EXAMS.includes(l.exam));

/**
 * Exam pages that are reachable by URL but not offered (not in `VISIBLE_EXAMS`): noindex, out of the sitemap, linked from nowhere.
 * Offer an exam again by adding it to `VISIBLE_EXAMS`.
 */
export const HIDDEN_EXAM_PATHS: readonly string[] = EXAM_LINKS.filter((l) => !VISIBLE_EXAMS.includes(l.exam)).map((l) => l.href);

/** The Legal column; the accessibility statement is linked from Company. */
export const FOOTER_LEGAL: readonly SiteLink[] = COMPLIANCE_DOCS.filter((d) => d.key !== "accessibility").map((d) => ({ href: d.href, label: d.footerLabel }));
