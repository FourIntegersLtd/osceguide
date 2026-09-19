import { platformRequest, type components } from "@/foundation/platform-client";
import type { RoomGrant } from "@/foundation/livekit";

export type OrgDashboard = components["schemas"]["OrgDashboard"];
export type Sitting = components["schemas"]["SittingRead"];
export type SittingPage = components["schemas"]["Page_SittingRead_"];
export type CircuitConsole = components["schemas"]["CircuitConsole"];
export type ConsoleSlot = components["schemas"]["ConsoleSlot"];
export type MySittings = components["schemas"]["MySittings"];
export type MySitting = components["schemas"]["MySitting"];
export type Trainee = components["schemas"]["TraineeRead"];

const org = (slug: string) => `/api/v1/orgs/${encodeURIComponent(slug)}`;

export function readOrgDashboard(slug: string, signal?: AbortSignal): Promise<OrgDashboard> {
  return platformRequest<OrgDashboard>(`${org(slug)}/dashboard`, { signal });
}

export function listSittings(slug: string, signal?: AbortSignal): Promise<SittingPage> {
  return platformRequest<SittingPage>(`${org(slug)}/sittings`, { signal });
}

export function readSitting(slug: string, sittingId: string, signal?: AbortSignal): Promise<Sitting> {
  return platformRequest<Sitting>(`${org(slug)}/sittings/${encodeURIComponent(sittingId)}`, {
    signal,
  });
}

export function readConsole(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<CircuitConsole> {
  return platformRequest<CircuitConsole>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/console`,
    { signal },
  );
}

/**
 * The supervisor's controls.
 *
 * Every one of these is a server-side state transition on the circuit, not a
 * local edit that is later saved. The old console kept the clock in the
 * supervisor's browser and broadcast it over LiveKit packets, so a refresh lost
 * the exam's timing and two supervisors disagreed about it.
 */
export const circuitActions = {
  start: (slug: string, circuitId: string) => act(slug, circuitId, "start"),
  advance: (slug: string, circuitId: string) => act(slug, circuitId, "advance"),
  pause: (slug: string, circuitId: string) => act(slug, circuitId, "pause"),
  resume: (slug: string, circuitId: string) => act(slug, circuitId, "resume"),
  end: (slug: string, circuitId: string) => act(slug, circuitId, "end"),
  resendPatient: (slug: string, circuitId: string) => act(slug, circuitId, "resend-patient"),
  resetClock: (slug: string, circuitId: string) => act(slug, circuitId, "reset-clock"),
};

function act(slug: string, circuitId: string, action: string): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/${action}`,
    { method: "POST" },
  );
}

export function extendClock(slug: string, circuitId: string, seconds: number): Promise<void> {
  return platformRequest<void>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/extend-clock`,
    { method: "POST", body: { seconds } },
  );
}

/** A room-admin token, so a supervisor can listen in without publishing. */
export function observerToken(
  slug: string,
  circuitId: string,
  signal?: AbortSignal,
): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `${org(slug)}/circuits/${encodeURIComponent(circuitId)}/observer-token`,
    { method: "POST", signal },
  );
}

export function listTrainees(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_TraineeRead_"]>(`${org(slug)}/trainees`, {
    signal,
  });
}

export function listMemberships(slug: string, signal?: AbortSignal) {
  return platformRequest<components["schemas"]["Page_MembershipRead_"]>(`${org(slug)}/memberships`, {
    signal,
  });
}

/* ---------- the trainee's side ---------- */

export function readMySittings(signal?: AbortSignal): Promise<MySittings> {
  return platformRequest<MySittings>("/api/v1/me/sittings", { signal });
}

/** Join the room for the circuit I am rostered onto. */
export function joinCircuit(circuitId: string, signal?: AbortSignal): Promise<RoomGrant> {
  return platformRequest<RoomGrant>(
    `/api/v1/me/circuits/${encodeURIComponent(circuitId)}/join-token`,
    { signal },
  );
}
