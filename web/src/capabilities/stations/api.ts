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

/** Ask the content team to review a library station. */
export async function flagStation(stationId: string, signal?: AbortSignal): Promise<void> {
  await platformRequest(`/api/v1/me/station-flags`, {
    method: "POST",
    body: JSON.stringify({ station_id: stationId }),
    signal,
  });
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
