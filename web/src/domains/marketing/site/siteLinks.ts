import { SUPPORT_EMAIL } from "@/foundation/support";
import { COMPLIANCE_DOCS } from "@/domains/marketing/legal/legalDocs";

export type SiteLink = { href: string; label: string };

const LANDING_ANCHORS = [
  { id: "features", label: "Features" },
  { id: "feedback", label: "Feedback" },
  { id: "exams", label: "Exams" },
  { id: "pricing", label: "Pricing" },
  { id: "faq", label: "FAQ" },
  { id: "stories", label: "Stories" },
] as const;

type AnchorId = (typeof LANDING_ANCHORS)[number]["id"];

/** Links to sections of the landing; `prefix` is "" on the landing itself and "/" elsewhere. */
function anchors(prefix: "" | "/", ids: readonly AnchorId[]): readonly SiteLink[] {
  return ids.map((id) => ({ href: `${prefix}#${id}`, label: LANDING_ANCHORS.find((a) => a.id === id)!.label }));
}

/** Centre links of the nav. On the landing they are anchors on the same page. */
export const LANDING_NAV_LINKS = [...anchors("", ["exams", "pricing"]), { href: "/institutions", label: "Institutions" }];

export const SITE_NAV_LINKS: readonly SiteLink[] = [
  { href: "/blogs", label: "Blogs" },
  ...anchors("/", ["exams", "pricing"]),
  { href: "/institutions", label: "Institutions" },
];

export const FOOTER_PRODUCT = anchors("/", ["features", "pricing", "faq", "stories"]);

export const FOOTER_COMPANY: readonly SiteLink[] = [
  { href: "/institutions", label: "For universities and programmes" },
  { href: "/login", label: "Log in" },
  { href: `mailto:${SUPPORT_EMAIL}`, label: "Contact us" },
  { href: "/compliances/accessibility", label: "Accessibility" },
];

/** Exam landings; `sca.osceguide.com` rewrites to the same pages. */
export const FOOTER_EXAMS: readonly SiteLink[] = [
  { href: "/exams/sca", label: "SCA (UK)" },
  { href: "/exams/plab", label: "PLAB 2 (UK)" },
  { href: "/exams/casc", label: "MRCPsych CASC" },
  { href: "/exams/ortho", label: "Orthopaedic ST3" },
];

/** The Legal column; the accessibility statement is linked from Company. */
export const FOOTER_LEGAL: readonly SiteLink[] = COMPLIANCE_DOCS.filter((d) => d.key !== "accessibility").map((d) => ({ href: d.href, label: d.footerLabel }));
