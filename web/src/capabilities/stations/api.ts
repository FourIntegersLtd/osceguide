import { platformRequest, type components } from "@/foundation/platform-client";

export type LibraryStation = components["schemas"]["LibraryStationRead"];
export type LibraryPage = components["schemas"]["Page_LibraryStationRead_"];
export type Exam = components["schemas"]["ExamRead"];

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

export function listExams(signal?: AbortSignal): Promise<components["schemas"]["Page_ExamRead_"]> {
  return platformRequest<components["schemas"]["Page_ExamRead_"]>("/api/v1/exams", { signal });
}
