import type { MediaKind } from "@/capabilities/media/api";
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

/** Consumer library route for preview (staff shell has no workspace). */
export function learnerMediaPreviewPath(
  item: Pick<MediaItem, "slug" | "exam_code">,
): string {
  const exam = (item.exam_code ?? "sca").toLowerCase();
  return `/app/${exam}/library/${encodeURIComponent(item.slug)}`;
}
