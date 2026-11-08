import { collectPages } from "@/capabilities/authoring/exams/examKind";
import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import type { Exam, ExamSettings, Programme } from "@/capabilities/authoring/api/scope";
import { examListPath, pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ------------------------------------------------------- exams, programmes */

/**
 * An organisation's list is published exams (its own and the platform's) by
 * default; `draft` is its own drafts, `all` its own in any status plus the
 * platform's published. The platform's list already returns every status.
 */
export function listExams(
  scope: AuthoringScope,
  params: { status?: "published" | "draft" | "all" } = {},
  signal?: AbortSignal,
): Promise<S["Page_ExamRead_"]> {
  const path = examListPath(scope);
  if (scope.kind === "org") {
    return platformRequest<S["Page_ExamRead_"]>(path, { query: { status: params.status }, signal });
  }
  // The platform's list takes `status` for the drafts question.
  return platformRequest<S["Page_ExamRead_"]>(path, {
    query: { status: params.status === "draft" ? "draft" : undefined, limit: 100 },
    signal,
  });
}

export function createExam(
  scope: AuthoringScope,
  body: {
    code: string;
    name: string;
    default_reading_seconds: number;
    default_simulation_seconds: number;
    station_attempt_limit: number;
    partner_pilot: boolean;
    rubric_version_id?: string | null;
    settings?: ExamSettings;
  },
): Promise<Exam> {
  return platformRequest(`${scope.base}/exams`, { method: "POST", body });
}

export function updateExam(
  scope: AuthoringScope,
  exam: string,
  body: {
    /** The revision the editor read; an older one is refused `stale_revision`. */
    revision: number;
  } & Partial<{
    name: string;
    default_reading_seconds: number;
    default_simulation_seconds: number;
    station_attempt_limit: number;
    partner_pilot: boolean;
    rubric_version_id: string | null;
    /** Replaces the whole object: send the exam's settings with the edits applied. */
    settings: ExamSettings;
  }>,
): Promise<Exam> {
  return platformRequest(`${scope.base}/exams/${pathId(exam)}`, { method: "PATCH", body });
}

export function publishExam(scope: AuthoringScope, exam: string): Promise<Exam> {
  return platformRequest(`${scope.base}/exams/${pathId(exam)}/publish`, { method: "POST" });
}

export function retireExam(scope: AuthoringScope, exam: string): Promise<Exam> {
  return platformRequest(`${scope.base}/exams/${pathId(exam)}/retire`, { method: "POST" });
}

/**
 * Remove a draft nothing was ever built on. Refuses (`exam_in_use`, 409) the
 * moment a station, sitting or attempt names it — `retireExam` above is the
 * lifecycle exit for those. Org exams only; the platform catalogue has no
 * delete at all, same as everywhere else in this scope.
 */
export function deleteExam(scope: AuthoringScope, exam: string): Promise<void> {
  return platformRequest(`${scope.base}/exams/${pathId(exam)}`, { method: "DELETE" });
}

export function listProgrammes(
  scope: AuthoringScope,
  signal?: AbortSignal,
  cursor?: string | null,
): Promise<S["Page_ProgrammeRead_"]> {
  const query = cursor ? `?cursor=${encodeURIComponent(cursor)}` : "";
  return platformRequest(`${scope.base}/programmes${query}`, { signal });
}

/** Every programme, page after page: a read of the first page alone misses an exam's programme past it. */
export async function listAllProgrammes(scope: AuthoringScope, signal?: AbortSignal): Promise<Programme[]> {
  const all: Programme[] = [];
  let cursor: string | null | undefined = null;
  do {
    const page: S["Page_ProgrammeRead_"] = await listProgrammes(scope, signal, cursor);
    all.push(...page.items);
    cursor = page.next_cursor;
  } while (cursor);
  return all;
}

export function addProgramme(scope: AuthoringScope, exam_code: string): Promise<Programme> {
  return platformRequest(`${scope.base}/programmes`, { method: "POST", body: { exam_code } });
}

export function updateProgramme(
  scope: AuthoringScope,
  programme: string,
  status: string,
): Promise<Programme> {
  return platformRequest(`${scope.base}/programmes/${pathId(programme)}`, {
    method: "PATCH",
    body: { status },
  });
}

/** Every sitting of the organisation, following the cursor so a long history is not cut at one page. */
export function listAllSittings(scope: AuthoringScope, signal?: AbortSignal): Promise<S["SittingRead"][]> {
  return collectPages((cursor) =>
    platformRequest<S["Page_SittingRead_"]>(`${scope.base}/sittings`, { query: { limit: 100, cursor }, signal }),
  );
}

/** One page of a programme's sittings. */
export function countProgrammeSittings(
  scope: AuthoringScope,
  programmeId: string,
  signal?: AbortSignal,
): Promise<S["Page_SittingRead_"]> {
  return platformRequest(`${scope.base}/sittings`, { query: { programme_id: programmeId, limit: 100 }, signal });
}
