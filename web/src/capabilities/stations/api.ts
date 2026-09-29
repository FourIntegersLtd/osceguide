import {
  hasCode,
  platformRequest,
  type components,
} from "@/foundation/platform-client";

export type LibraryStation = components["schemas"]["LibraryStationRead"];
export type LibraryPage = components["schemas"]["Page_LibraryStationRead_"];
export type Exam = components["schemas"]["ExamRead"];
export type ExamPage = components["schemas"]["Page_ExamRead_"];
export type StationFlag = components["schemas"]["StationFlagRead"];
export type StationVersion = components["schemas"]["StationVersionRead"];

/**
 * A comment on a station.
 *
 * The same `posts` row the discussion board is built from — the backend files
 * a station comment under the station's id instead of a parent question, so
 * there is one moderation path and one like count rather than the separate
 * `station_comments` collection the retiring client wrote to.
 */

/**
 * The stations anyone signed in may practise.
 *
 * One library, whoever is asking. The old clients had two sources — four
 * Firestore collections keyed by product for consumers, and an institution
 * backend that reached across into them — so a station could exist for one
 * audience and not the other. Here `owner_kind` distinguishes platform from
 * org-authored and the query is the same.
 *
 * `search` is a fragment of a title, matched in SQL. It used to be applied in
 * the browser to whatever pages had already been fetched, which meant "no
 * results" only ever meant "not on the first two thousand".
 */
export function browseLibrary(
  params: {
    examCode?: string | null;
    search?: string | null;
    cursor?: string | null;
    limit?: number;
  },
  signal?: AbortSignal,
): Promise<LibraryPage> {
  const search = params.search?.trim();
  return platformRequest<LibraryPage>("/api/v1/stations", {
    query: {
      exam_code: params.examCode ?? undefined,
      search: search ? search : undefined,
      cursor: params.cursor ?? undefined,
      limit: params.limit,
    },
    signal,
  });
}

export function listExams(signal?: AbortSignal): Promise<ExamPage> {
  return platformRequest<ExamPage>("/api/v1/exams", { signal });
}

/** The practice session a flag was raised inside, when there was one. */
export interface FlagSetEntry {
  setId: string;
  entryId: string;
}

/**
 * Ask the content team to review a station.
 *
 * `from` names the session entry the station was sat in, so the reporter's
 * Flagged tab can reopen it there. `FlagStationBody` takes `station_id` only
 * and ignores the rest today, so the two ids are dropped until the backend
 * stores them (see `docs/BACKLOG.md`, "flagged stations open the library").
 */
export async function flagStation(
  stationId: string,
  from?: FlagSetEntry | null,
  signal?: AbortSignal,
): Promise<void> {
  await platformRequest(`/api/v1/me/station-flags`, {
    method: "POST",
    // An object: `platformRequest` serialises it. This used to pass
    // `JSON.stringify(...)`, which serialised a *string* — so the request the
    // button made was rejected before it reached a handler that discarded it.
    body: from
      ? { station_id: stationId, set_id: from.setId, set_entry_id: from.entryId }
      : { station_id: stationId },
    signal,
  });
}

/**
 * What this person has reported, newest first.
 *
 * The route used to be served by `identity` and thrown away, so the runner's
 * button confirmed a report nobody received; this is the read that proves it
 * landed, and the source of the "Flagged stations" list.
 */
export function myStationFlags(signal?: AbortSignal): Promise<StationFlag[]> {
  return platformRequest<StationFlag[]>("/api/v1/me/station-flags", { signal });
}

/**
 * One station by id.
 *
 * `GET /api/v1/stations/{id}` answers with the same row the browse page gives
 * — a title and the two ids needed to bind an attempt — and none of the
 * document inside it: browsing the library is not reading the answers. Until
 * the route existed a station opened by link was found by walking the browse
 * list a hundred rows at a time in the browser, which capped what a shared
 * link could reach at whatever the walk covered and answered "not found" for
 * anything past it.
 *
 * A station the caller may not read answers `station_not_found`, and so does
 * one that never existed. That is returned as `null` rather than raised,
 * because the screens already have a sentence for it — "we could not find that
 * station" — and a withdrawn case is not a failure of the request. Every other
 * refusal still raises, so a 500 is still a visible failure.
 */
export async function readLibraryStation(
  stationId: string,
  signal?: AbortSignal,
): Promise<LibraryStation | null> {
  try {
    return await platformRequest<LibraryStation>(
      `/api/v1/stations/${encodeURIComponent(stationId)}`,
      { signal },
    );
  } catch (cause) {
    if (hasCode(cause, "station_not_found")) return null;
    throw cause;
  }
}

/**
 * Every revision one station has had, newest first.
 *
 * The lifecycle could draft, publish, supersede and archive a version and had
 * no reader for any of it, so the author's screen could not offer a previous
 * one. Each row here is a whole document — the patient's persona and the
 * examiner's material, including the drafts nobody settled on — which is why
 * the endpoint answers staff only: an organisation's admin reading their own
 * station, or a platform admin curating the library. Anything else is
 * `forbidden`, and that arrives as an error rather than an empty history, so a
 * refusal cannot be read as a station that was never revised.
 */
export function listStationVersions(
  stationId: string,
  signal?: AbortSignal,
): Promise<StationVersion[]> {
  return platformRequest<StationVersion[]>(
    `/api/v1/stations/${encodeURIComponent(stationId)}/versions`,
    { signal },
  );
}
