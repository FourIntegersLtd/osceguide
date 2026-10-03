/**
 * What the backend hands back to get a browser into a room.
 *
 * `voice` is the only slice that mints tokens and decides whether the session
 * is served by LiveKit Cloud or our own workers, so the browser never chooses
 * a server URL and never learns which worker family answered.
 */
export interface RoomGrant {
  room: string;
  server_url: string;
  token: string;
  /**
   * Whether this grant may publish audio/video. Always `true` for a
   * candidate's own grant. For an observer it now varies with the sitting's
   * mode (training vs exam) — see `sittings/service_join.py:observer_token`
   * — so a caller must read it rather than assume subscribe-only.
   */
  can_publish?: boolean;
}

/** The agent states LiveKit reports, in the words a candidate should read. */
export const AGENT_STATE_LABEL: Record<string, string> = {
  disconnected: "Not connected",
  connecting: "Connecting to the patient…",
  initializing: "Getting the patient ready…",
  "pre-connect-buffering": "Getting the patient ready…",
  listening: "The patient is listening",
  thinking: "The patient is thinking…",
  speaking: "The patient is speaking",
  failed: "The patient couldn't join",
};

/**
 * The label for a state. `speaker` names who is on the line when it is not the
 * patient (Athena on the tour); the default keeps the consultation's wording.
 */
export function agentStateLabel(state: string | undefined, speaker?: string): string {
  const label = AGENT_STATE_LABEL[state ?? "disconnected"] ?? "Connected";
  return speaker ? label.replace("The patient", speaker).replace("the patient", speaker) : label;
}
