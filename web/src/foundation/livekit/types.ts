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

export function agentStateLabel(state: string | undefined): string {
  return AGENT_STATE_LABEL[state ?? "disconnected"] ?? "Connected";
}
