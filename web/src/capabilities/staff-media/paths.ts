import { PERSONAL_SLUG } from "@/foundation/routing";
import { isMediaKind, type MediaKind } from "@/capabilities/media/api";
import { studyItemHref } from "@/capabilities/media/studyPaths";
import type { MediaItem } from "@/capabilities/staff-media/api";

export function staffMediaDetailPath(itemId: string): string {
  return `/staff/media/${encodeURIComponent(itemId)}`;
}

/** The study material list, open on one kind's tab. */
export function staffMediaListPath(kind: MediaKind): string {
  return `/staff/media?kind=${encodeURIComponent(kind)}`;
}

export function staffMediaNewPath(kind: MediaKind): string {
  return `/staff/media?new=1&kind=${encodeURIComponent(kind)}`;
}

/** Where a learner opens the item, in their own workspace (the staff shell has none). */
export function learnerMediaPreviewPath(item: Pick<MediaItem, "kind" | "slug">): string {
  const kind = isMediaKind(item.kind) ? item.kind : "summary";
  return studyItemHref((path) => `/app/${PERSONAL_SLUG}${path}`, kind, item.slug);
}
