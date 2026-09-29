import { platformRequest, type components } from "@/foundation/platform-client";
import {
  collectPages,
  orgPath,
  pageQuery,
  readSitting,
  type Sitting,
  type SittingPage,
} from "@/domains/assess/api";
import {
  circuitsStartedOn,
  sittingNearDay,
  type PastCircuit,
} from "@/domains/assess/dashboard/support";

export type OrgDashboard = components["schemas"]["OrgDashboard"];
export type OrgSetup = components["schemas"]["OrgSetup"];
export type OrgSittingRow = components["schemas"]["OrgSittingRow"];
export type LiveBoard = components["schemas"]["LiveBoard"];
export type LiveCircuit = components["schemas"]["LiveCircuit"];
export type SupervisorCircuits = components["schemas"]["SupervisorCircuits"];
export type SupervisorCircuitRow = components["schemas"]["SupervisorCircuitRow"];

export function readOrgDashboard(slug: string, signal?: AbortSignal): Promise<OrgDashboard> {
  return platformRequest<OrgDashboard>(`${orgPath(slug)}/dashboard`, { signal });
}

/**
 * Every examination this organisation has running, in one request.
 *
 * The screen that did not exist. On the morning of an OSCE a course lead could
 * open one circuit's console, or a list of sittings that did not say which were
 * live — so "how is the morning going" was answered by walking between rooms.
 *
 * Staff only, and deliberately: the board names every candidate and how they
 * are doing, which is not a thing a candidate may read about the people beside
 * them.
 */
export function readLiveBoard(slug: string, signal?: AbortSignal): Promise<LiveBoard> {
  return platformRequest<LiveBoard>(`${orgPath(slug)}/live`, { signal });
}

/**
 * The board, pushed.
 *
 * One subscription for the whole organisation rather than one per circuit, and
 * frames arrive when something changes rather than on a tick — which is why
 * every row carries `phase_ends_at` and the screen counts down from it between
 * frames instead of waiting to be told the time.
 */
export function liveBoardStreamPath(slug: string): string {
  return `${orgPath(slug)}/live/stream`;
}

/** The circuits this person is named supervisor on. */
export function readSupervisorCircuits(
  slug: string,
  signal?: AbortSignal,
): Promise<SupervisorCircuits> {
  return platformRequest<SupervisorCircuits>(`${orgPath(slug)}/supervisor/circuits`, { signal });
}

/**
 * What ran on one day, finished or not.
 *
 * `/live` answers now only. There is no history route, but every circuit on a
 * sitting carries `started_at` and `ended_at`, so this reads the sittings
 * scheduled near the day and keeps the circuits that started on it. The
 * sitting list carries no circuits, hence one read per nearby sitting.
 */
export async function readCircuitsOnDay(
  slug: string,
  day: string,
  signal?: AbortSignal,
): Promise<PastCircuit[]> {
  const sittings = await collectPages((cursor) =>
    platformRequest<SittingPage>(`${orgPath(slug)}/sittings`, {
      signal,
      query: pageQuery({ cursor }),
    }),
  );
  const nearby: Sitting[] = await Promise.all(
    sittings
      .filter((sitting) => sittingNearDay(sitting, day))
      .map((sitting) => readSitting(slug, sitting.id, signal)),
  );
  return circuitsStartedOn(nearby, day);
}
