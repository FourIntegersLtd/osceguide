import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type {
  StationTemplate,
  StationTemplateVersion,
} from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";
import { toPlatformStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

/**
 * platform-api's renderer reads a flat `blocks` list with a `role` per block
 * and a template-level `layout`; the editor works in `sections`. Send both,
 * so the document round-trips through the editor and renders by role.
 */
function platformStructure(structure: Json | undefined): Json | undefined {
  if (!structure || typeof structure !== "object" || !("sections" in structure)) return structure;
  return toPlatformStructure(structure as unknown as StationStructure) as unknown as Json;
}

type S = components["schemas"];

/* ------------------------------------------------------- station templates */

const TEMPLATE_MAX_PAGES = 20;

/**
 * Every template in this scope.
 *
 * The route answers the whole list with `next_cursor: null` today. Following
 * the cursor anyway means the day it pages, this still returns every template
 * rather than silently the first page; the pickers that use it need them all.
 */
export async function listStationTemplates(
  scope: AuthoringScope,
  signal?: AbortSignal,
): Promise<S["Page_StationTemplateRead_"]> {
  const items: StationTemplate[] = [];
  let cursor: string | null = null;
  for (let page = 0; page < TEMPLATE_MAX_PAGES; page += 1) {
    const result: S["Page_StationTemplateRead_"] = await platformRequest(
      `${scope.base}/station-templates`,
      { query: { cursor: cursor ?? undefined }, signal },
    );
    items.push(...result.items);
    cursor = result.next_cursor ?? null;
    if (!cursor) break;
  }
  return { items, next_cursor: null };
}

export function createStationTemplate(
  scope: AuthoringScope,
  body: { title: string; exam_code?: string | null; structure?: Json },
): Promise<StationTemplate> {
  return platformRequest(`${scope.base}/station-templates`, {
    method: "POST",
    body: { ...body, structure: platformStructure(body.structure) },
  });
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
  title?: string,
): Promise<StationTemplateVersion> {
  return platformRequest(`${scope.base}/station-templates/${pathId(template)}/versions/${version}`, {
    method: "PATCH",
    body: {
      structure: platformStructure(structure),
      ...(title !== undefined ? { title } : {}),
    },
  });
}

export function deleteStationTemplateVersion(
  scope: AuthoringScope,
  template: string,
  version: number,
): Promise<void> {
  return platformRequest(`${scope.base}/station-templates/${pathId(template)}/versions/${version}`, {
    method: "DELETE",
  });
}

export function archiveStationTemplateVersion(
  scope: AuthoringScope,
  template: string,
  version: number,
): Promise<StationTemplateVersion> {
  return platformRequest(
    `${scope.base}/station-templates/${pathId(template)}/versions/${version}/archive`,
    { method: "POST" },
  );
}
