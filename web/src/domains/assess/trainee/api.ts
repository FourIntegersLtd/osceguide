import {
  platformDownload,
  platformRequest,
  type PlatformDownload,
  type components,
} from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";
import { collectPages, orgPath, pageQuery } from "@/domains/assess/api";

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
export type MySlot = components["schemas"]["MySlot"];
export type TraineeResult = components["schemas"]["TraineeResultRead"];
export type OrgStation = components["schemas"]["StationRead"];

/**
 * Not yet in `schema.d.ts` — `npm run platform:types` hasn't run against the
 * backend's new `/me/slots/{id}/review` route. Inline until it has.
 */
export type MySlotReview = {
  slot_id: string;
  summary: {
    slot_id: string;
    overall_rag: string | null;
    by_domain: Record<string, string>;
    completed_reviews: number;
  };
  notes: string | null;
  completed_at: string | null;
};

/** Pushed, not polled. The old detail screen re-fetched every five seconds. */
export const MY_SITTINGS_STREAM = "/api/v1/me/sittings/stream";

export function readMySittings(signal?: AbortSignal): Promise<MySittings> {
  return platformRequest<MySittings>("/api/v1/me/sittings", { signal });
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

export function readMyResult(sittingId: string, signal?: AbortSignal): Promise<TraineeResult> {
  return platformRequest<TraineeResult>(`/api/v1/me/results/${encodeURIComponent(sittingId)}`, {
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

/** This candidate's own review of one of their slots, once a GP lead has
 * completed one — not before. */
export function readMyReview(slotId: string, signal?: AbortSignal): Promise<MySlotReview> {
  return platformRequest<MySlotReview>(`/api/v1/me/slots/${encodeURIComponent(slotId)}/review`, {
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
