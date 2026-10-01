import { feedbackReviewHref } from "@/capabilities/pending-feedback";

/** Where a station was opened from: a practice set, the library, or an organisation's own practice. */
export type StationSource =
  | { kind: "set"; setId: string; entryId: string }
  | { kind: "practice"; stationId: string }
  | { kind: "self_practice"; orgSlug: string; stationId: string };

/** A name for this station that is the same on every visit, used to remember its attempt. */
export function stationKeyFor(source: StationSource): string {
  if (source.kind === "set") return `${source.setId}:${source.entryId}`;
  if (source.kind === "practice") return `practice:${source.stationId}`;
  return `self:${source.orgSlug}:${source.stationId}`;
}

/** The page that shows the feedback for an attempt, before the surface adds its own prefix. */
export function feedbackPathFor(source: StationSource, attemptId: string): string {
  if (source.kind === "set") return feedbackReviewHref(source.setId, source.entryId, attemptId);
  if (source.kind === "practice") {
    return `/stations/${source.stationId}/practise?action=review&tab=feedback&attempt=${attemptId}`;
  }
  return `/attempts/${attemptId}`;
}
