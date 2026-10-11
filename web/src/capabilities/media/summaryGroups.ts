import { specialtiesOf, type MediaItem } from "@/capabilities/media/api";

export type SummaryView = "az" | "specialty";

function groupByLetter(items: readonly MediaItem[]): Record<string, MediaItem[]> {
  const sorted = [...items].sort((a, b) => a.title.localeCompare(b.title));
  return sorted.reduce<Record<string, MediaItem[]>>((acc, item) => {
    const letter = item.title.charAt(0).toUpperCase();
    (acc[letter] ??= []).push(item);
    return acc;
  }, {});
}

/**
 * An item with several specialties appears under each of them, as it did
 * before. Items with none are left out entirely rather than gathered under
 * "Unknown": on this backend that is every item, and a single bucket holding
 * the whole library is worse than an empty state that says so.
 */
function groupBySpecialty(items: readonly MediaItem[]): Record<string, MediaItem[]> {
  return items.reduce<Record<string, MediaItem[]>>((acc, item) => {
    for (const specialty of specialtiesOf(item)) {
      (acc[specialty] ??= []).push(item);
    }
    return acc;
  }, {});
}

export type SummaryGroups = Record<string, MediaItem[]>;

export function summaryGroups(items: readonly MediaItem[], view: SummaryView): Record<string, MediaItem[]> {
  return view === "az" ? groupByLetter(items) : groupBySpecialty(items);
}

/** The jump-link row: one link per group, in order. Fewer than two groups need no row. */
export function jumpLinks(groups: Record<string, unknown[]>): { key: string; href: string }[] {
  const keys = Object.keys(groups).sort();
  return keys.length > 1 ? keys.map((key) => ({ key, href: `#summary-${key}` })) : [];
}
