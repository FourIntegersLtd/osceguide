/**
 * The groups the sidebar draws, in the order it draws them.
 *
 * Consumer arms use practice, connect and general. The staff console groups
 * by the question being asked — who is the customer (customers), where is the
 * money (revenue), what do people practise with (catalogue), is the platform
 * healthy (operations) — with Overview ungrouped above the headings.
 *
 * It lives in this tier rather than beside the surface manifests because a
 * capability names its own section — study material is catalogue, discussion
 * is people — and a capability may not import a surface. An arm whose items
 * name no section gets a flat list, which is what the institution arms want.
 */
export const NAV_SECTIONS = [
  "customers",
  "revenue",
  "catalogue",
  "operations",
  "practice",
  "connect",
  "general",
] as const;

export type NavSection = (typeof NAV_SECTIONS)[number];

/**
 * The breadcrumb's one label map: a nav section's name (by section id) and a page reached from
 * inside a section rather than from the nav (by first path segment). The two key sets do not overlap.
 */
export const NAV_LABELS: Record<string, string> = {
  customers: "Customers",
  revenue: "Revenue",
  catalogue: "Catalogue",
  operations: "Operations",
  practice: "Practice",
  connect: "Connect",
  general: "General",
  debriefs: "Debriefs",
  transcripts: "Transcripts",
  library: "Library",
  stations: "Station",
  attempts: "Attempt",
  sessions: "Sessions",
  sittings: "Sittings",
  circuits: "Circuit",
  slots: "Review",
  trainee: "My training",
  mocks: "Practice sessions",
};
