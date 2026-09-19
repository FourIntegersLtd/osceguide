import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope } from "@/capabilities/authoring/api/scope";
import type { Exam, Programme } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ------------------------------------------------------- exams, programmes */

export function listExams(
  scope: AuthoringScope,
  params: { drafts?: boolean } = {},
  signal?: AbortSignal,
): Promise<S["Page_ExamRead_"]> {
  return platformRequest(`${scope.base}/exams`, { query: { drafts: params.drafts }, signal });
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
  },
): Promise<Exam> {
  return platformRequest(`${scope.base}/exams`, { method: "POST", body });
}

export function updateExam(
  scope: AuthoringScope,
  exam: string,
  body: Partial<{
    name: string;
    default_reading_seconds: number;
    default_simulation_seconds: number;
    station_attempt_limit: number;
    partner_pilot: boolean;
    rubric_version_id: string | null;
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

export function listProgrammes(
  scope: AuthoringScope,
  signal?: AbortSignal,
): Promise<S["Page_ProgrammeRead_"]> {
  return platformRequest(`${scope.base}/programmes`, { signal });
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
