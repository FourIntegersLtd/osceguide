import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath, pageQuery } from "@/domains/assess/api";

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

export type LiveRun = components["schemas"]["LiveRunRead"];
export type LiveRunPage = components["schemas"]["Page_LiveRunRead_"];

/**
 * Circuits that have finished, newest first, a page at a time.
 *
 * The board is built from what is running, so a circuit that ended used to
 * leave nothing behind; each end now writes a row the board can look back on.
 */
export function readLiveHistory(
  slug: string,
  cursor: string | null,
  signal?: AbortSignal,
): Promise<LiveRunPage> {
  return platformRequest<LiveRunPage>(`${orgPath(slug)}/live/history`, {
    signal,
    query: pageQuery({ cursor, limit: 25 }),
  });
}
