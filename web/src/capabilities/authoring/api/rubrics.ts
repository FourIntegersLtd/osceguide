import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type { Rubric, RubricVersion } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ----------------------------------------------------------------- rubrics */

export function listRubrics(
  scope: AuthoringScope,
  params: { cursor?: string | null } = {},
  signal?: AbortSignal,
): Promise<S["Page_RubricRead_"]> {
  return platformRequest(`${scope.base}/rubrics`, {
    query: { cursor: params.cursor ?? undefined },
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

export function createRubric(
  scope: AuthoringScope,
  body: {
    title: string;
    system_prompt: string;
    structure: Json;
    pacing: Json;
    result_schema_override?: Json | null;
    marking_layout?: Json | null;
  },
): Promise<Rubric> {
  return platformRequest(`${scope.base}/rubrics`, { method: "POST", body });
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
    result_schema_override?: Json | null;
    marking_layout?: Json | null;
  },
): Promise<RubricVersion> {
  return platformRequest(`${scope.base}/rubrics/${pathId(rubric)}/versions/${version}`, {
    method: "PATCH",
    body,
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
