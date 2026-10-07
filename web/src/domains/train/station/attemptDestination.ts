/** The part of an attempt's brief that says where it was sat. */
export interface SatAt {
  station_id?: string | null;
  set_entry_id?: string | null;
}

export type AttemptDestination =
  | { kind: "set_entry"; setId: string; entryId: string }
  | { kind: "station"; stationId: string }
  | { kind: "unknown" };

/**
 * Where an attempt is read. A session's station is read inside its session; if that session
 * cannot be found, the attempt is not sent to the station's single-practice page (it was not
 * sat there), and one with no station at all goes nowhere rather than to `/stations/null`.
 */
export function attemptDestination(brief: SatAt, setId: string | null): AttemptDestination {
  if (brief.set_entry_id) {
    return setId ? { kind: "set_entry", setId, entryId: brief.set_entry_id } : { kind: "unknown" };
  }
  return brief.station_id ? { kind: "station", stationId: brief.station_id } : { kind: "unknown" };
}

/** Whether a session's station can be sat, read back, or neither, by what the catalogue still holds. */
export function setStationState(input: {
  entry: unknown;
  station: unknown;
  action: "attempt" | "review";
}): "ok" | "unknown_entry" | "retired" {
  if (!input.entry) return "unknown_entry";
  // A retired station can still be read back from an attempt already sat.
  if (!input.station && input.action === "attempt") return "retired";
  return "ok";
}
