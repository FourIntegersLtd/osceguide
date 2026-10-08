import {
  collectPages,
  platformDownload,
  platformRequest,
  type PlatformDownload,
  type components,
} from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import { orgPath, pageQuery } from "@/domains/assess/api";

/**
 * Everything a rostered person reads about their own training.
 *
 * All of it hangs off `/me` rather than `/orgs/{slug}`, which is the point:
 * what a candidate may see about their own sitting is one decision on the
 * server, not a filter applied in the browser to an organisation's data. The
 * retiring arm fetched the org's session list and then removed the rows whose
 * `traineeId` did not match, so a bug in that filter was a disclosure.
 *
 * The one exception is the station list for self practice, which is an
 * organisation's library and is read as one.
 */

export type MySittings = components["schemas"]["MySittings"];
export type MySitting = components["schemas"]["MySitting"];
// `marking_failed` (T-3) is declared here until the generated types are regenerated.
export type MySlot = components["schemas"]["MySlot"] & { marking_failed?: boolean };
export type TraineeResult = components["schemas"]["TraineeResultRead"];
export type OrgStation = components["schemas"]["StationRead"];

/** A candidate's released review of one station, in the rubric's own rating kind (`summary.rating`). */
export type MySlotReview = components["schemas"]["MySlotReviewRead"];

/** `org_slug` is declared on these routes but not yet in the generated types (until regenerated). */
function orgQuery(orgSlug: string | null): string {
  return orgSlug ? `?org_slug=${encodeURIComponent(orgSlug)}` : "";
}

/** Pushed, not polled. The old detail screen re-fetched every five seconds. */
export function mySittingsStreamPath(orgSlug: string | null): string {
  return `/api/v1/me/sittings/stream${orgQuery(orgSlug)}`;
}

/** One workspace's sittings (a trainee in two organisations sees each in its own), or all when none is named. */
export function readMySittings(orgSlug: string | null, signal?: AbortSignal): Promise<MySittings> {
  return platformRequest<MySittings>(`/api/v1/me/sittings${orgQuery(orgSlug)}`, { signal });
}

/** Join the room for a circuit I am rostered onto. */
export function joinCircuit(circuitId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/me/circuits/${encodeURIComponent(circuitId)}/join-token`,
    // POST, like the route: the grant is minted per request, not read. The
    // client's default is GET, and a GET here answers 405 — which is what
    // kept every candidate out of every room on exam day.
    { method: "POST", signal },
  );
}

export type SlotBrief = components["schemas"]["SlotBriefRead"];

/** What this candidate reads for one of their slots once the circuit reaches it (B50). */
export function readSlotBrief(slotId: string, signal?: AbortSignal): Promise<SlotBrief> {
  return platformRequest<SlotBrief>(`/api/v1/me/slots/${encodeURIComponent(slotId)}/brief`, {
    signal,
  });
}

/** This candidate's released result, or `null` until it is released. */
export function readMyResult(sittingId: string, signal?: AbortSignal): Promise<TraineeResult | null> {
  return platformRequest<TraineeResult | null>(`/api/v1/me/results/${encodeURIComponent(sittingId)}`, {
    signal,
  });
}

/** This candidate's released result as a PDF the browser saves. */
export function downloadMyResult(sittingId: string): Promise<PlatformDownload> {
  return platformDownload(`/api/v1/me/results/${encodeURIComponent(sittingId)}.pdf`);
}

export function acknowledgeResult(sittingId: string): Promise<void> {
  return platformRequest<void>(
    `/api/v1/me/results/${encodeURIComponent(sittingId)}/acknowledge`,
    { method: "POST" },
  );
}

/** This candidate's own review of one of their slots once a GP lead has
 * completed it and the result is released; `null` before. */
export function readMyReview(slotId: string, signal?: AbortSignal): Promise<MySlotReview | null> {
  return platformRequest<MySlotReview | null>(`/api/v1/me/slots/${encodeURIComponent(slotId)}/review`, {
    signal,
  });
}

/**
 * The organisation's own stations, for practising alone.
 *
 * `GET /orgs/{slug}/stations` is an `OrgReader` route, and that predicate
 * admits a trainee — so this is the trainee's list as much as the author's.
 * The platform library is a different endpoint and a different screen: the
 * stations capability, mounted on this arm already.
 */
export function listOrgStations(slug: string, signal?: AbortSignal): Promise<OrgStation[]> {
  return collectPages<OrgStation>((cursor) =>
    platformRequest<components["schemas"]["Page_StationRead_"]>(`${orgPath(slug)}/stations`, {
      signal,
      query: pageQuery({ cursor }),
    }),
  );
}
