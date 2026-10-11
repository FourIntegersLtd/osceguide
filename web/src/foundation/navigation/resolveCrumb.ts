import { isNavActive } from "@/foundation/navigation/isNavActive";

interface CrumbItem {
  href: string;
  label: string;
  section?: string | null;
}

/**
 * The breadcrumb for a path: the longest nav item the path sits under (so
 * `/summary/asthma` reads under A to Z), else a named deep page, else Dashboard.
 */
export function resolveCrumb({
  pathname,
  items,
  basePath,
  sectionLabels,
  rootLabel,
  deepPages,
}: {
  pathname: string;
  items: readonly CrumbItem[];
  basePath: string;
  sectionLabels: Record<string, string>;
  rootLabel: string;
  /** Page names for the first path segment of pages reached from inside a section, not from the nav. */
  deepPages: Record<string, string>;
}): { section: string; page: string } {
  const match = items
    .filter((item) => isNavActive(pathname, item.href, { shellBase: basePath }))
    .sort((a, b) => b.href.length - a.href.length)[0];
  if (match) {
    return { section: match.section ? (sectionLabels[match.section] ?? rootLabel) : rootLabel, page: match.label };
  }
  const segment = pathname.slice(basePath.length).split("/").filter(Boolean)[0] ?? "";
  return { section: rootLabel, page: deepPages[segment] ?? "Dashboard" };
}
