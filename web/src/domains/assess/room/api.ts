import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath } from "@/domains/assess/api";

export type Scheme = components["schemas"]["SchemeRead"];
export type PeerMarks = components["schemas"]["PeerMarksRead"];
export type PeerMarkIn = components["schemas"]["PeerMarkIn"];

const circuit = (slug: string, circuitId: string) => `${orgPath(slug)}/circuits/${encodeURIComponent(circuitId)}`;

/** The supervisor opens the floor to every microphone, or closes it back to the one whose turn it is. */
export function setFloor(slug: string, circuitId: string, open: boolean): Promise<unknown> {
  return platformRequest(`${circuit(slug, circuitId)}/floor`, { method: "POST", body: { open } });
}

/** One person's microphone: allowed or muted by the supervisor, whoever's turn it is. */
export function setParticipantMic(slug: string, circuitId: string, identity: string, allowed: boolean): Promise<unknown> {
  return platformRequest(`${circuit(slug, circuitId)}/participants/${encodeURIComponent(identity)}/mic`, {
    method: "POST",
    body: { allowed },
  });
}

/** Ends the room for everyone once a training circuit has ended. */
export function closeRoom(slug: string, circuitId: string): Promise<unknown> {
  return platformRequest(`${circuit(slug, circuitId)}/room/close`, { method: "POST", body: {} });
}

/** The marking scheme of the station running now, for the supervisor. */
export function readSchemeForStaff(slug: string, circuitId: string, signal?: AbortSignal): Promise<Scheme> {
  return platformRequest<Scheme>(`${circuit(slug, circuitId)}/scheme`, { signal });
}

/** The same, for a trainee waiting for their turn (the one sitting reads their brief instead). */
export function readSchemeForTrainee(circuitId: string, signal?: AbortSignal): Promise<Scheme> {
  return platformRequest<Scheme>(`/api/v1/me/circuits/${encodeURIComponent(circuitId)}/scheme`, { signal });
}

/** A trainee watching another's turn saves marks on it; the answer is everything they have marked so far. */
export function savePeerMarks(circuitId: string, slotId: string, marks: PeerMarkIn[]): Promise<PeerMarks> {
  return platformRequest<PeerMarks>(
    `/api/v1/me/circuits/${encodeURIComponent(circuitId)}/slots/${encodeURIComponent(slotId)}/peer-marks`,
    { method: "PUT", body: { marks } },
  );
}

/** Every watching trainee's marks on one turn, for the supervisor. */
export function readPeerMarksForStaff(slug: string, circuitId: string, slotId: string, signal?: AbortSignal): Promise<PeerMarks> {
  return platformRequest<PeerMarks>(`${circuit(slug, circuitId)}/slots/${encodeURIComponent(slotId)}/peer-marks`, { signal });
}

/** What fellow trainees marked on my turn; empty until its feedback is shared. */
export function readMyPeerMarks(slotId: string, signal?: AbortSignal): Promise<PeerMarks> {
  return platformRequest<PeerMarks>(`/api/v1/me/slots/${encodeURIComponent(slotId)}/peer-marks`, { signal });
}
