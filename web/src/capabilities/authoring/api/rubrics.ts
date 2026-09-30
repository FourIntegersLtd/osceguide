import { platformRequest, platformStream, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type { Rubric, RubricVersion } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ----------------------------------------------------------------- rubrics */

/**
 * One page of this scope's rubrics.
 *
 * Shaped like `listStations`: `search` matches a title fragment and
 * `exam_code` keeps only rubrics bound to that exam's published version, both
 * run in SQL rather than filtered in the browser.
 */
export function listRubrics(
  scope: AuthoringScope,
  params: { cursor?: string | null; limit?: number; search?: string | null; exam_code?: string | null } = {},
  signal?: AbortSignal,
): Promise<S["Page_RubricRead_"]> {
  return platformRequest(`${scope.base}/rubrics`, {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit,
      search: params.search?.trim() || undefined,
      exam_code: params.exam_code || undefined,
    },
    signal,
  });
}

export function readRubric(
  scope: AuthoringScope,
  rubric: string,
  signal?: AbortSignal,
): Promise<Rubric> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}`, { signal });
}

export function addRubricVersion(scope: AuthoringScope, rubric: string): Promise<RubricVersion> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}/versions`, { method: "POST" });
}

export function editRubricVersion(
  scope: AuthoringScope,
  rubric: string,
  version: number,
  body: {
    system_prompt: string;
    structure: Json;
    pacing: Json;
    marking_layout?: Json | null;
  },
): Promise<RubricVersion> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}/versions/${version}`, {
    method: "PATCH",
    body,
  });
}

/**
 * Change a rubric's title (R-7). Every version keeps it, so this touches only
 * the rubric row, never a version, and the builder can call it any time a
 * draft or published version is open.
 */
export function renameRubric(scope: AuthoringScope, rubric: string, title: string): Promise<Rubric> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}`, {
    method: "PATCH",
    body: { title },
  });
}

export function archiveRubricVersion(
  scope: AuthoringScope,
  rubric: string,
  version: number,
): Promise<RubricVersion> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}/versions/${version}/archive`, {
    method: "POST",
  });
}

export function publishRubricVersion(
  scope: AuthoringScope,
  rubric: string,
  version: number,
): Promise<RubricVersion> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}/versions/${version}/publish`, {
    method: "POST",
  });
}

/* ------------------------------------------------------- the rubric builder */

export type RubricProblem = S["RubricProblemRead"];
export type RubricPreview = S["RubricPreviewRead"];
export type RubricStartingPoint = S["RubricStartingPointRead"];
export type DraftInstruction = S["DraftInstructionRead"];
export type TrialMark = S["TrialMarkRead"];
export type TrialMarkRequest = S["TrialMarkRequest"];

/**
 * What a new rubric can start from: blank first, then the platform's
 * published rubrics, then (inside an organisation) its own. `search` is a
 * title fragment matched on the server — never filter the loaded list here.
 */
export function listRubricStartingPoints(
  scope: AuthoringScope,
  search: string,
  signal?: AbortSignal,
): Promise<S["RubricStartingPointsRead"]> {
  return platformRequest(`${scope.base}/rubrics/starting-points`, {
    query: { search: search.trim() || undefined },
    signal,
  });
}

/**
 * Everything a draft structure comes to — whether it can be published, every
 * problem at its path, the resolved display and a sample result to draw the
 * feedback with. Never refused, so it is also the builder's validation call.
 */
export function previewRubric(scope: AuthoringScope, structure: Json, signal?: AbortSignal): Promise<RubricPreview> {
  return platformRequest(`${scope.base}/rubrics/preview`, { method: "POST", body: { structure }, signal });
}

/**
 * A new draft rubric of this scope's own: a copy of a published rubric, or
 * blank when no source is named. Answers 201 with the rubric and its first
 * draft version.
 */
export function copyRubric(
  scope: AuthoringScope,
  body: S["CopyRubric"],
): Promise<Rubric> {
  return platformRequest(`${scope.base}/rubrics/copy`, { method: "POST", body });
}

/** Suggested instructions for every place in a structure that carries them. */
export function draftRubricInstructions(scope: AuthoringScope, structure: Json): Promise<S["DraftInstructionsRead"]> {
  return platformRequest(`${scope.base}/rubrics/draft-instructions`, { method: "POST", body: { structure } });
}

export type TrialCandidate = S["TrialCandidateRead"];

/**
 * A page of attempts this scope could trial-mark against (R-6): what fills
 * the trial panel's attempt picker. `search` matches the candidate's name,
 * email or the station's title, matched on the server — never filter the
 * loaded page here.
 */
export function listTrialCandidates(
  scope: AuthoringScope,
  params: { cursor?: string | null; limit?: number; search?: string | null } = {},
  signal?: AbortSignal,
): Promise<S["Page_TrialCandidateRead_"]> {
  return platformRequest(`${scope.base}/rubrics/trial-candidates`, {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit,
      search: params.search?.trim() || undefined,
    },
    signal,
  });
}

/**
 * Trial-mark one version (a draft included) against a pasted transcript or an
 * attempt, streaming progress. Each `snapshot` frame is handed to `onSnapshot`
 * as it arrives: `marking` every few seconds, then `marked` or `failed`.
 * Nothing is stored. A refusal before the stream opens throws a
 * `PlatformError` (`invalid_rubric`, `invalid_trial_transcript`, 429,
 * `marker_unavailable`).
 */
export function trialMarkRubricVersion(
  scope: AuthoringScope,
  rubric: string,
  version: number,
  body: TrialMarkRequest,
  onSnapshot: (snapshot: TrialMark) => void,
  signal?: AbortSignal,
): Promise<void> {
  return platformStream(
    `${scope.base}/rubrics/${pathId(rubric)}/versions/${version}/trial`,
    { method: "POST", body, signal },
    (frame) => {
      if (frame.event !== "snapshot") return;
      onSnapshot(JSON.parse(frame.data) as TrialMark);
    },
  );
}
