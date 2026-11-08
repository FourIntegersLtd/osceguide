/** What a tile in the training room says, decided once and tested: identities, names and the calm line about whose turn it is. */

export type RoomRole = "patient" | "supervisor" | "trainee";

export const roleOf = (identity: string): RoomRole =>
  identity.startsWith("agent-") ? "patient" : identity.startsWith("observer-") ? "supervisor" : "trainee";

/** The name on a tile: the viewer is always "You", the patient is "Patient". */
export function tileName({ role, name, isSelf }: { role: RoomRole; name?: string; isSelf: boolean }): string {
  if (isSelf) return "You";
  if (role === "patient") return "Patient";
  const shown = name?.trim();
  // A token without a display name shows the identity, which is an id and not a person.
  const isId = !shown || /^(observer-)?[0-9a-f]{8}-[0-9a-f]{4}-/i.test(shown);
  return isId ? (role === "supervisor" ? "Supervisor" : "Trainee") : shown;
}

export type TileStatus = "speaking" | "muted" | "idle";

/** Speaking wins; a person who may not speak reads as muted; the patient is never muted. */
export function tileStatus({ role, micAllowed, speaking }: { role: RoomRole; micAllowed: boolean; speaking: boolean }): TileStatus {
  if (speaking) return "speaking";
  return role !== "patient" && !micAllowed ? "muted" : "idle";
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export interface RoomPerson {
  role: RoomRole;
  name: string;
  isSelf: boolean;
  micAllowed: boolean;
}

/**
 * The one calm line about whose turn it is. The floor is open when every trainee in the room may speak
 * (with two or more of them, so one trainee alone is simply their turn).
 */
export function turnLine(people: readonly RoomPerson[]): { line: string; floorOpen: boolean } {
  const trainees = people.filter((p) => p.role === "trainee");
  const speakers = trainees.filter((p) => p.micAllowed);
  if (trainees.length >= 2 && speakers.length === trainees.length) {
    return { line: "The floor is open. Everyone can speak.", floorOpen: true };
  }
  const mine = speakers.find((p) => p.isSelf);
  if (mine) return { line: "It's your turn.", floorOpen: false };
  const [only] = speakers;
  if (only && speakers.length === 1) return { line: `${only.name}'s turn.`, floorOpen: false };
  return { line: "Waiting for the next turn.", floorOpen: false };
}
