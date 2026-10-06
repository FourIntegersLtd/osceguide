import { isPlatformError } from "@/foundation/platform-client";
import type { LibraryPage, LibraryStation } from "@/capabilities/stations/api";

export const PLATFORM_PREFIX = "platform:";

export interface LibraryLegs {
  /** The organisation's own stations. */
  org: (cursor: string | null) => Promise<LibraryPage>;
  /** The platform's stations for the exam. */
  platform: (cursor: string | null) => Promise<LibraryPage>;
}

const EMPTY: LibraryPage = { items: [], next_cursor: null };

/**
 * One page of an organisation's library: its own stations first, then the
 * platform's for the exam. The cursor says which list it belongs to, so "Load
 * more" walks one list to its end and on to the next. An exam the organisation
 * cannot offer from the platform refuses with 403 `not_entitled`, which is an empty leg;
 * any other failure is raised. `includePlatform: false` stops after the org's own list.
 */
export async function pageAcrossLegs(
  legs: LibraryLegs,
  includePlatform: boolean,
  cursor: string | null,
): Promise<LibraryPage> {
  if (cursor?.startsWith(PLATFORM_PREFIX)) {
    return platformLeg(legs, cursor.slice(PLATFORM_PREFIX.length) || null);
  }
  const own = await legs.org(cursor);
  if (own.next_cursor || !includePlatform) return own;
  const platform = await platformLeg(legs, null);
  return { items: [...own.items, ...platform.items], next_cursor: platform.next_cursor };
}

async function platformLeg(legs: LibraryLegs, cursor: string | null): Promise<LibraryPage> {
  try {
    const page = await legs.platform(cursor);
    return { ...page, next_cursor: page.next_cursor ? PLATFORM_PREFIX + page.next_cursor : null };
  } catch (cause) {
    if (isPlatformError(cause) && cause.status === 403 && cause.code === "not_entitled") return EMPTY;
    throw cause;
  }
}

/** Each station once, first seen wins. An org page and a platform page can overlap when a station is both the org's own and a platform exam's. */
export function uniqueById(stations: readonly LibraryStation[]): LibraryStation[] {
  const seen = new Set<string>();
  return stations.filter((station) => !seen.has(station.id) && seen.add(station.id));
}
