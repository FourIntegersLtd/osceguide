import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type {
  StationTemplate,
  StationTemplateVersion,
  FeedbackTemplate,
  FeedbackTemplateVersion,
} from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";

type S = components["schemas"];

/* ------------------------------------------------------- station templates */

export function listStationTemplates(
  scope: AuthoringScope,
  signal?: AbortSignal,
): Promise<S["Page_StationTemplateRead_"]> {
  return platformRequest(`${scope.base}/station-templates`, { signal });
}

export function createStationTemplate(
  scope: AuthoringScope,
  body: { title: string; exam_code?: string | null; structure?: Json },
): Promise<StationTemplate> {
  return platformRequest(`${scope.base}/station-templates`, { method: "POST", body });
}

export function publishStationTemplate(
  scope: AuthoringScope,
  template: string,
): Promise<StationTemplateVersion> {
  return platformRequest(`${scope.base}/station-templates/${pathId(template)}/publish`, {
    method: "POST",
  });
}

export function addStationTemplateVersion(
  scope: AuthoringScope,
  template: string,
): Promise<StationTemplateVersion> {
  return platformRequest(`${scope.base}/station-templates/${pathId(template)}/versions`, {
    method: "POST",
  });
}

export function editStationTemplateVersion(
  scope: AuthoringScope,
  template: string,
  version: number,
  structure: Json,
): Promise<StationTemplateVersion> {
  return platformRequest(`${scope.base}/station-templates/${pathId(template)}/versions/${version}`, {
    method: "PATCH",
    body: { structure },
  });
}

/* ------------------------------------------------------ feedback templates */

export function listFeedbackTemplates(
  scope: AuthoringScope,
  signal?: AbortSignal,
): Promise<S["Page_FeedbackTemplateRead_"]> {
  return platformRequest(`${scope.base}/feedback-templates`, { signal });
}

export function createFeedbackTemplate(
  scope: AuthoringScope,
  body: { title: string; rubric_version_id: string; field_selection?: Json },
): Promise<FeedbackTemplate> {
  return platformRequest(`${scope.base}/feedback-templates`, { method: "POST", body });
}

export function publishFeedbackTemplate(
  scope: AuthoringScope,
  template: string,
): Promise<FeedbackTemplateVersion> {
  return platformRequest(`${scope.base}/feedback-templates/${pathId(template)}/publish`, {
    method: "POST",
  });
}

export function addFeedbackTemplateVersion(
  scope: AuthoringScope,
  template: string,
): Promise<FeedbackTemplateVersion> {
  return platformRequest(`${scope.base}/feedback-templates/${pathId(template)}/versions`, {
    method: "POST",
  });
}

export function editFeedbackTemplateVersion(
  scope: AuthoringScope,
  template: string,
  version: number,
  field_selection: Json,
): Promise<FeedbackTemplateVersion> {
  return platformRequest(`${scope.base}/feedback-templates/${pathId(template)}/versions/${version}`, {
    method: "PATCH",
    body: { field_selection },
  });
}
