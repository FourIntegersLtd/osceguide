import { podcastGroupLabel, type MediaItem } from "@/capabilities/media/api";

/** A to Z and Podcasts show this many rows, then this many more under "Load more". */
export const CLIENT_PAGE_SIZE = 10;

export function sortByTitle(items: readonly MediaItem[]): MediaItem[] {
  return [...items].sort((a, b) => a.title.localeCompare(b.title));
}

/** Episodes grouped by series label, groups and episodes both in title order. */
export function groupPodcasts(items: readonly MediaItem[]): { label: string; episodes: MediaItem[] }[] {
  const groups = new Map<string, MediaItem[]>();
  for (const item of items) {
    const label = podcastGroupLabel(item);
    groups.set(label, [...(groups.get(label) ?? []), item]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([label, episodes]) => ({ label, episodes: sortByTitle(episodes) }));
}

/** The order the page lists episodes in; the player's Previous and Next walk it too. */
export function podcastOrder(items: readonly MediaItem[]): MediaItem[] {
  return groupPodcasts(items).flatMap((group) => group.episodes);
}
