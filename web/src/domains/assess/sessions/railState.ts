/** Which right-hand rail sections a person has opened, remembered per browser. */
export type RailOpen = Record<string, boolean>;

const KEY = "circuit-console-rail";

/** Reads a stored value; anything that is not a map of booleans is dropped. */
export function parseRail(raw: string | null): RailOpen {
  if (!raw) return {};
  try {
    const value: unknown = JSON.parse(raw);
    if (typeof value !== "object" || value === null || Array.isArray(value)) return {};
    return Object.fromEntries(Object.entries(value).filter(([, v]) => typeof v === "boolean"));
  } catch {
    return {};
  }
}

export const toggleRail = (open: RailOpen, id: string): RailOpen => ({ ...open, [id]: !open[id] });

export function loadRail(): RailOpen {
  try {
    return parseRail(window.localStorage.getItem(KEY));
  } catch {
    return {};
  }
}

export function saveRail(open: RailOpen): void {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(open));
  } catch {
    /* private window or blocked storage: the page works without it */
  }
}
