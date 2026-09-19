/**
 * The groups the sidebar draws, in the order it draws them.
 *
 * The retiring consumer client had exactly these, with these labels, and the
 * grouping is most of why a sidebar of nine items reads as three short lists
 * rather than one long one.
 *
 * It lives in this tier rather than beside the surface manifests because a
 * capability names its own section — study material is practice, discussion is
 * people — and a capability may not import a surface. An arm whose items name
 * no section gets a flat list, which is what the institution arms want.
 */
export const NAV_SECTIONS = ["practice", "connect", "general"] as const;

export type NavSection = (typeof NAV_SECTIONS)[number];

export const NAV_SECTION_LABELS: Record<NavSection, string> = {
  practice: "Practice",
  connect: "Connect",
  general: "General",
};
