import { platformRequest, type components } from "@/foundation/platform-client";
import type { AuthoringScope, Json } from "@/capabilities/authoring/api/scope";
import type { Station, StationVersion } from "@/capabilities/authoring/api/scope";
import { pathId } from "@/capabilities/authoring/api/scope";
import { explainArchiveRefusal } from "@/capabilities/authoring/api/archiveRefusal";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

type S = components["schemas"];

/* ---------------------------------------------------------------- stations */

/** The backend's page cap. */
export const STATION_PAGE_LIMIT = 100;

/**
 * One page of this scope's stations.
 *
 * `search` matches a title fragment in SQL and `exam_code` narrows to one
 * exam, so finding one station in a catalogue of thousands is one request
 * rather than loading all of it and filtering in the browser. `include_archived`
 * defaults to false: the catalogue view hides archived stations unless a
 * caller asks to see them.
 */
export function listStations(
  scope: AuthoringScope,
  params: {
    cursor?: string | null;
    limit?: number;
    search?: string | null;
    exam_code?: string | null;
    include_archived?: boolean;
  } = {},
  signal?: AbortSignal,
): Promise<S["Page_StationRead_"]> {
  return platformRequest(`${scope.base}/stations`, {
    query: {
      cursor: params.cursor ?? undefined,
      limit: params.limit,
      search: params.search?.trim() || undefined,
      exam_code: params.exam_code || undefined,
      include_archived: params.include_archived ?? false,
    },
    signal,
  });
}

export function autogenerateStationDraft(
  scope: AuthoringScope,
  body: { prompt: string; template_version_id: string },
): Promise<{ suggested_title: string; content: Record<string, unknown> }> {
  return platformRequest(`${scope.base}/stations/autogenerate-draft`, {
    method: "POST",
    body,
  });
}

export function createStation(
  scope: AuthoringScope,
  body: { title: string; exam_code: string; content: Json; template_version_id?: string | null },
): Promise<Station> {
  return platformRequest(`${scope.base}/stations`, { method: "POST", body });
}

export function addStationVersion(scope: AuthoringScope, station: string): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions`, { method: "POST" });
}

/**
 * `facts` is the fact check with the reader's rulings on it, saved with the corrections they made.
 * `title` renames the station.
 */
export function editStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
  content: Json,
  extra: { facts?: Record<string, unknown>; title?: string } = {},
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}`, {
    method: "PATCH",
    body: { content, ...extra },
  });
}

export type StationReview = S["StationReview"];

/** A catalogue station version's fact check. See `supportsFactCheck`. */
export function readStationReview(
  scope: AuthoringScope,
  station: string,
  version: number,
  signal?: AbortSignal,
): Promise<StationReview> {
  return platformRequest(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/review`,
    { signal },
  );
}

/** Starts a fact check; `station.updated` arrives on `/me/events` when it settles. */
export function checkStationFacts(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<StationReview> {
  return platformRequest(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/check-facts`,
    { method: "POST" },
  );
}

/**
 * Starts the agent on a catalogue station's draft: it drafts from the brief
 * when there is nothing written, checks the facts and corrects what the
 * sources contradict. `station.updated` arrives after every step.
 */
export function produceStation(
  scope: AuthoringScope,
  station: string,
  version: number,
  input: S["ProduceRequest"],
): Promise<StationReview> {
  return platformRequest(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/produce`,
    { method: "POST", body: input },
  );
}

/** Asks the agent to stop after the step it is on. */
export function stopProducingStation(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<StationReview> {
  return platformRequest(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/stop-produce`,
    { method: "POST" },
  );
}

export function deleteStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<void> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}`, {
    method: "DELETE",
  });
}

export function archiveStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
  w: AssessWords,
): Promise<StationVersion> {
  return platformRequest<StationVersion>(`${scope.base}/stations/${pathId(station)}/versions/${version}/archive`, {
    method: "POST",
  }).catch((cause: unknown) => {
    throw explainArchiveRefusal(cause, w);
  });
}

/**
 * An editor's sign-off on a published station: approved stations reach the library, the rest stay
 * out of it. Staff only, so only the platform scope has the routes.
 */
export function setStationApproval(
  scope: AuthoringScope,
  station: string,
  approved: boolean,
): Promise<Station> {
  if (approved) {
    return platformRequest(`${scope.base}/stations/${pathId(station)}/approve`, { method: "POST" });
  }
  return platformRequest(`${scope.base}/stations/${pathId(station)}/revoke-approval`, { method: "POST" });
}

export function publishStationVersion(
  scope: AuthoringScope,
  station: string,
  version: number,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}/publish`, {
    method: "POST",
  });
}

/**
 * Correct the reading brief without cutting a new version.
 *
 * The brief is what a candidate is handed before the station starts, so a typo
 * in one does not invalidate what everybody else was marked against.
 */
export function editStationBrief(
  scope: AuthoringScope,
  station: string,
  version: number,
  reading_brief: string,
): Promise<StationVersion> {
  return platformRequest(`${scope.base}/stations/${pathId(station)}/versions/${version}/brief`, {
    method: "PATCH",
    body: { reading_brief },
  });
}

/**
 * Write a station from a prompt, with no template behind it.
 *
 * The platform's own generation route — the staff half of the legacy
 * "auto-station" screen. It answers content shaped by the exam's structure and
 * nothing else, so the caller treats the result as a filled-in draft: the
 * author still reads it, and still has to save it.
 *
 * `template_version_id` is optional on `CreateStation`, which is what makes a
 * template-less station legal at all. The create screen used to refuse to open
 * until a template existed, so this route had no caller and an author could not
 * write a one-off case without first authoring a reusable template for it.
 */
export function generateStation(input: {
  prompt: string;
  examCode: string;
  stationSubtype?: string | null;
}): Promise<{ content: Json }> {
  return platformRequest<{ content: Json }>("/api/v1/platform/generate/station", {
    method: "POST",
    body: {
      prompt: input.prompt,
      exam_code: input.examCode,
      // Only meaningful for exams whose settings declare station subtypes; the
      // backend ignores it otherwise. Sent as null rather than omitted so the
      // absence is explicit.
      station_subtype: input.stationSubtype ?? null,
    },
  });
}

/* ------------------------------------------------------- station photos */

export type StationPhotosResult = S["StationPhotosResult"];

/**
 * Put images on one media block of a station's version.
 *
 * The field name is `files`, repeated once per image — the backend's
 * parameter name, and the same one the retiring uploader sent. A partial
 * upload comes back as a result rather than an error: the images that worked
 * are on the station and `failed` names the rest.
 */
export function uploadStationPhotos(
  scope: AuthoringScope,
  station: string,
  version: number,
  blockId: string,
  files: File[],
): Promise<StationPhotosResult> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return platformRequest<StationPhotosResult>(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/photos?block=${encodeURIComponent(blockId)}`,
    { method: "POST", formData: form },
  );
}

/** Take one image off a station, and out of the bucket. */
export function removeStationPhoto(
  scope: AuthoringScope,
  station: string,
  version: number,
  photoUrl: string,
): Promise<StationVersion> {
  return platformRequest<StationVersion>(
    `${scope.base}/stations/${pathId(station)}/versions/${version}/photos/remove`,
    { method: "POST", body: { photo_url: photoUrl } },
  );
}
