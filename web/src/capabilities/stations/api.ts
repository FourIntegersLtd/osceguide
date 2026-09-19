import { platformRequest, type components } from "@/foundation/platform-client";

export type LibraryStation = components["schemas"]["LibraryStationRead"];
export type LibraryPage = components["schemas"]["Page_LibraryStationRead_"];
export type Exam = components["schemas"]["ExamRead"];
export type ExamPage = components["schemas"]["Page_ExamRead_"];

/**
 * A comment on a station.
 *
 * The same `posts` row the discussion board is built from — the backend files
 * a station comment under the station's id instead of a parent question, so
 * there is one moderation path and one like count rather than the separate
 * `station_comments` collection the retiring client wrote to.
 */
export type StationComment = components["schemas"]["app__features__community__schemas__PostRead"];
export type StationCommentPage = components["schemas"]["app__core__pagination__Page_PostRead___2"];

/**
 * The stations anyone signed in may practise.
 *
 * One library, whoever is asking. The old clients had two sources — four
 * Firestore collections keyed by product for consumers, and an institution
 * backend that reached across into them — so a station could exist for one
 * audience and not the other. Here `owner_kind` distinguishes platform from
 * org-authored and the query is the same.
 */
export function browseLibrary(
  params: { examCode?: string | null; cursor?: string | null; limit?: number },
  signal?: AbortSignal,
): Promise<LibraryPage> {
  return platformRequest<LibraryPage>("/api/v1/stations", {
    query: {
      exam_code: params.examCode ?? undefined,
      cursor: params.cursor ?? undefined,
      limit: params.limit,
    },
    signal,
  });
}

export function listExams(signal?: AbortSignal): Promise<ExamPage> {
  return platformRequest<ExamPage>("/api/v1/exams", { signal });
}

/** How many library pages `findLibraryStation` will walk before giving up. */
const FIND_PAGE_LIMIT = 100;
const FIND_MAX_PAGES = 20;

/**
 * One station by id.
 *
 * There is no `GET /api/v1/stations/{id}` for a learner — the library is a
 * browse list and the per-station reads are all authoring routes behind an
 * organisation's permissions. So a station opened by link is found by walking
 * the same list the browse screen already pages through, which is bounded and
 * cheap because a page is a title and two ids, and it means a shared link
 * works rather than 404ing. See `docs/port-gaps.md`.
 */
export async function findLibraryStation(
  stationId: string,
  signal?: AbortSignal,
): Promise<LibraryStation | null> {
  let cursor: string | null = null;

  for (let page = 0; page < FIND_MAX_PAGES; page += 1) {
    const result: LibraryPage = await browseLibrary(
      { cursor, limit: FIND_PAGE_LIMIT },
      signal,
    );
    const found = result.items.find((station) => station.id === stationId);
    if (found) return found;
    cursor = result.next_cursor ?? null;
    if (!cursor) return null;
  }

  return null;
}

/**
 * What other candidates said about this station.
 *
 * Readable by anyone who can see the station, which is what makes this part of
 * the capability rather than of the consumer arm: an institution's trainees
 * discuss the same scenario in the same thread.
 */
export function listStationComments(
  stationId: string,
  signal?: AbortSignal,
): Promise<StationCommentPage> {
  return platformRequest<StationCommentPage>(
    `/api/v1/stations/${encodeURIComponent(stationId)}/comments`,
    { signal },
  );
}

export function commentOnStation(
  stationId: string,
  input: { body: string; orgId?: string | null },
): Promise<StationComment> {
  return platformRequest<StationComment>(
    `/api/v1/stations/${encodeURIComponent(stationId)}/comments`,
    {
      method: "POST",
      body: {
        body: input.body,
        // An organisation's workspace keeps its own thread; a personal one
        // posts to the public board. The audience is the backend's, so the
        // capability passes what the surface gave it and decides nothing.
        audience: input.orgId
          ? { visibility: "organisation", org_id: input.orgId }
          : { visibility: "public", org_id: null },
      },
    },
  );
}
