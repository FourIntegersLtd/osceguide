import { platformRequest, type components } from "@/foundation/platform-client";

import { browseLibrary, type LibraryStation } from "@/capabilities/stations";

export type Dashboard = components["schemas"]["Dashboard"];
export type StationSet = components["schemas"]["SetRead"];
export type SetPage = components["schemas"]["Page_SetRead_"];
export type SetEntry = components["schemas"]["EntryRead"];
export type StartedAttempt = components["schemas"]["StartedAttempt"];
export type Entitlement = components["schemas"]["EntitlementSummary"];
export type Plan = components["schemas"]["PlanRead"];
export type SetAllowance = components["schemas"]["SetAllowance"];

/** The whole home screen in one request. */
export function readDashboard(signal?: AbortSignal): Promise<Dashboard> {
  return platformRequest<Dashboard>("/api/v1/me/dashboard", { signal });
}

export function listSets(signal?: AbortSignal, cursor?: string | null): Promise<SetPage> {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return platformRequest<SetPage>(`/api/v1/me/station-sets${query}`, { signal });
}

export function readSet(setId: string, signal?: AbortSignal): Promise<StationSet> {
  return platformRequest<StationSet>(`/api/v1/me/station-sets/${encodeURIComponent(setId)}`, {
    signal,
  });
}

/** How many new stations a session for this exam may hold: the free trial's stations left, or null when paid. */
export function readSetAllowance(examCode: string, signal?: AbortSignal): Promise<SetAllowance> {
  return platformRequest<SetAllowance>(
    `/api/v1/me/station-sets/allowance?exam_code=${encodeURIComponent(examCode)}`,
    { signal },
  );
}

/**
 * Flag one station in a set to come back to, or take the flag off.
 *
 * The learner's own list (the Flagged tab), and separate from reporting a
 * station as wrong, which goes to the content team (`flagStation`).
 */
export function flagSetEntry(setId: string, entryId: string, flagged: boolean): Promise<StationSet> {
  return platformRequest<StationSet>(
    `/api/v1/me/station-sets/${encodeURIComponent(setId)}/entries/${encodeURIComponent(entryId)}/flag`,
    { method: "PUT", body: { flagged } },
  );
}

export type FlaggedEntry = components["schemas"]["FlaggedEntryRead"];

/**
 * A page of `FlaggedEntry`. Generated types are stale here — `schema.d.ts`
 * still shows this route returning a bare array with no query params — so
 * the shape is declared by hand rather than read off `components["schemas"]`,
 * the same way `domains/platform/support/api.ts` does for a live route ahead
 * of its generated type.
 */
export interface FlaggedEntryPage {
  items: FlaggedEntry[];
  next_cursor?: string | null;
}

/**
 * A page of the stations this person has flagged across their sets, most
 * recent first. `search` matches the station title in SQL, so a growing
 * flag list is narrowed on the server rather than by walking every page.
 */
export function listFlaggedStations(
  params: { cursor?: string | null; limit?: number; search?: string | null },
  signal?: AbortSignal,
): Promise<FlaggedEntryPage> {
  return platformRequest<FlaggedEntryPage>("/api/v1/me/flagged-stations", {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit,
      search: params.search?.trim() || undefined,
    },
    signal,
  });
}

export function createSet(input: {
  name: string;
  examCode: string;
  stationVersionIds: string[];
}): Promise<StationSet> {
  return platformRequest<StationSet>("/api/v1/me/station-sets", {
    method: "POST",
    body: {
      name: input.name,
      exam_code: input.examCode,
      station_version_ids: input.stationVersionIds,
    },
  });
}

/**
 * Change a session's name and the stations in it, in one PATCH.
 *
 * The station list is sent whole. The server keeps the entries that are still
 * in it (with the attempts that point at them), adds the new ones, drops the
 * rest and numbers them again in the order given. The server refuses a locked
 * session (`set_locked`), dropping a station somebody has already sat
 * (`set_entry_has_attempts`), and a station that cannot be practised
 * (`station_version_not_usable`), all before changing anything. The page shows
 * the server's own sentence for each.
 */
export function updateSet(
  setId: string,
  input: { name: string; stationVersionIds: string[] },
): Promise<StationSet> {
  return platformRequest<StationSet>(`/api/v1/me/station-sets/${encodeURIComponent(setId)}`, {
    method: "PATCH",
    body: { name: input.name, station_version_ids: input.stationVersionIds },
  });
}

/**
 * Throw a session away.
 *
 * A set somebody has started a station in answers 409 `set_has_attempts` rather
 * than being emptied: its recordings would be left pointing at rows that have
 * gone. The caller shows the backend's own sentence for that and does not
 * retry — asking again gets the same answer.
 */
export async function deleteSet(setId: string): Promise<void> {
  await platformRequest<void>(`/api/v1/me/station-sets/${encodeURIComponent(setId)}`, {
    method: "DELETE",
  });
}

/**
 * Start an attempt at one entry.
 *
 * The counter is incremented in SQL inside the attempt's transaction, so two
 * taps cannot both be allowed past the limit.
 */
export function startSetAttempt(setId: string, entryId: string): Promise<StartedAttempt> {
  return platformRequest<StartedAttempt>(
    `/api/v1/me/station-sets/${encodeURIComponent(setId)}/entries/${encodeURIComponent(entryId)}/attempts`,
    { method: "POST" },
  );
}

/**
 * What the free trial allows. Declared here until the generated schema carries the new `trial`
 * field of `GET /me/entitlements`; swap for the generated type then.
 */
export interface TrialLimits {
  stations: number;
  days: number;
  attempts_per_station: number;
}

/** What this person may practise, and what the free trial allows. The mocks screens gate on it. */
export function listEntitlements(signal?: AbortSignal) {
  return platformRequest<{ items: Entitlement[]; trial: TrialLimits }>("/api/v1/me/entitlements", { signal });
}

/*
 * Plans and receipts are read by the account capability, not here. They
 * describe the person rather than the arm, and the readers that used to sit in
 * this file typed `GET /me/receipts` as a page of receipts when it is a page
 * of receipt *ids* — so every field on the access screen rendered undefined.
 * `capabilities/account/api.ts` has the correct pair.
 */

/* ------------------------------------------------------------------------
 * Performance analytics
 *
 * `GET /api/v1/me/performance` is the consumer half of what the retiring
 * backend served from `/api/{exam}_dashboard`: a pass/fail/critical summary, a
 * score per rubric domain and a trend line.
 *
 * Generated, not hand-written. These were written by hand while the endpoint
 * was being built in parallel; now that it exists they point at the schema, so
 * a field the backend renames breaks the build here rather than rendering an
 * empty chart.
 *
 * `exam_code` is nullable on purpose, and only in one case: the caller named
 * no exam and has never attempted one, so there is no exam to report on. An
 * empty string would have been a code, which is worse.
 * --------------------------------------------------------------------- */

export type Performance = components["schemas"]["Performance"];
export type PerformanceSummary = components["schemas"]["PerformanceSummary"];
export type PerformanceDomain = components["schemas"]["DomainScore"];
export type PerformanceTrendPoint = components["schemas"]["TrendPoint"];

/**
 * One exam's marked performance. A failure of any kind, a 404 included, is raised: the endpoint
 * exists, so "nothing came back" must reach the screen as a failure with a retry, never pass
 * for an empty dashboard.
 */
export function readPerformance(examCode: string, signal?: AbortSignal): Promise<Performance> {
  return platformRequest<Performance>("/api/v1/me/performance", {
    query: { exam_code: examCode },
    signal,
  });
}

/** The library's own page cap. Asking for more is a 422, not a longer page. */
const LIBRARY_PAGE = 100;

/**
 * Every published station for an exam, paged.
 *
 * A set entry carries a station version id and no title, so every mocks screen
 * needs the whole catalogue to render a name. `browse_library` caps a page at
 * 100 — the rebuilt screens asked for 200 and got a 422 on every load, which
 * is why the mocks list rendered as "The request was not valid" — so this
 * follows the cursor instead, bounded so a runaway catalogue cannot hang a
 * screen.
 */
export async function loadStationCatalogue(
  examCode: string | null,
  signal?: AbortSignal,
  maxPages = 10,
): Promise<LibraryStation[]> {
  const items: LibraryStation[] = [];
  let cursor: string | null = null;
  for (let page = 0; page < maxPages; page += 1) {
    const result = await browseLibrary({ examCode, cursor, limit: LIBRARY_PAGE }, signal);
    items.push(...result.items);
    cursor = result.next_cursor ?? null;
    if (!cursor) break;
  }
  return items;
}
