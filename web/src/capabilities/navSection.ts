/**
 * The groups the sidebar draws, in the order it draws them.
 *
 * Consumer arms use practice, connect and general. The staff console adds
 * platform, catalogue and content & growth — three short lists rather than one
 * long one.
 *
 * It lives in this tier rather than beside the surface manifests because a
 * capability names its own section — study material is practice, discussion is
 * people — and a capability may not import a surface. An arm whose items name
 * no section gets a flat list, which is what the institution arms want.
 */
export const NAV_SECTIONS = [
  "console",
  "catalogue",
  "content",
  "practice",
  "connect",
  "general",
] as const;

export type NavSection = (typeof NAV_SECTIONS)[number];

export const NAV_SECTION_LABELS: Record<NavSection, string> = {
  console: "Platform",
  catalogue: "Catalogue",
  content: "Content & growth",
  practice: "Practice",
  connect: "Connect",
  general: "General",
};
