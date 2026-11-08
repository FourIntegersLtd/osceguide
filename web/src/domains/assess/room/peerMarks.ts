/** Peer marks: the pure parts. A mark is one rating and/or comment on `domainId` or `domainId.competencyId`. */
import type { PeerMarkIn, PeerMarks } from "@/domains/assess/room/api";

export const PEER_RATINGS = [
  { value: "G", label: "Met" },
  { value: "A", label: "Partly" },
  { value: "R", label: "Not met" },
] as const;

export const ratingWord = (value: string): string => PEER_RATINGS.find((r) => r.value === value)?.label ?? value;

export type PeerState = Record<string, { rating: string | null; comment: string | null }>;

interface Outline {
  id?: string;
  title?: string;
  competencies?: { id?: string; label?: string }[];
}

export const peerItem = (domainId: string, competencyId?: string): string =>
  competencyId ? `${domainId}.${competencyId}` : domainId;

/** The state the server holds for me (the PUT answers with only my marks). */
export function stateFrom(marks: PeerMarks | null): PeerState {
  const state: PeerState = {};
  for (const mark of marks?.items ?? []) state[mark.item] = { rating: mark.rating ?? null, comment: mark.comment ?? null };
  return state;
}

/** One change applied; choosing the rating already chosen clears it. */
export function withMark(state: PeerState, item: string, patch: { rating?: string | null; comment?: string | null }): PeerState {
  const current = state[item] ?? { rating: null, comment: null };
  const rating = patch.rating === undefined ? current.rating : patch.rating === current.rating ? null : patch.rating;
  const comment = patch.comment === undefined ? current.comment : patch.comment;
  return { ...state, [item]: { rating, comment: comment ? comment : null } };
}

export const marksFor = (state: PeerState, items: string[]): PeerMarkIn[] =>
  items.filter((item) => item in state).map((item) => ({ item, ...state[item] }));

/** item to the words a supervisor reads: "Domain" or "Domain: competency". */
export function itemLabels(outline: Outline[]): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const domain of outline) {
    if (!domain.id) continue;
    labels[domain.id] = domain.title ?? domain.id;
    for (const competency of domain.competencies ?? [])
      if (competency.id) labels[peerItem(domain.id, competency.id)] = `${domain.title ?? domain.id}: ${competency.label ?? competency.id}`;
  }
  return labels;
}

export interface MarkerGroup {
  markerId: string;
  name: string;
  rows: { item: string; label: string; rating: string | null; comment: string | null }[];
}

/** Marks grouped by whoever made them, in the scheme's own order; an item the scheme no longer has keeps its key. */
export function byMarker(marks: PeerMarks | null, labels: Record<string, string>): MarkerGroup[] {
  const order = Object.keys(labels);
  const groups = new Map<string, MarkerGroup>();
  for (const mark of marks?.items ?? []) {
    if (!mark.rating && !mark.comment) continue;
    const group = groups.get(mark.marker_id) ?? { markerId: mark.marker_id, name: mark.marker_name, rows: [] };
    group.rows.push({ item: mark.item, label: labels[mark.item] ?? mark.item, rating: mark.rating ?? null, comment: mark.comment ?? null });
    groups.set(mark.marker_id, group);
  }
  const rank = (item: string) => (order.indexOf(item) === -1 ? order.length : order.indexOf(item));
  return [...groups.values()]
    .map((group) => ({ ...group, rows: group.rows.sort((a, b) => rank(a.item) - rank(b.item)) }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** What a trainee reads for each mark: the domain's title (competency titles are not in the review), never an id. */
export function feedbackLabels(marks: PeerMarks | null, domainTitles: Record<string, string>): Record<string, string> {
  return Object.fromEntries(
    (marks?.items ?? []).map((m) => [m.item, domainTitles[m.item.split(".")[0] ?? ""] ?? "Other feedback"]),
  );
}
