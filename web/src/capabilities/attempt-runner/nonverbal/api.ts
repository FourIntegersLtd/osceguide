import { platformRequest, type components } from "@/foundation/platform-client";

export type NonverbalRead = components["schemas"]["NonverbalRead"];
export type NonverbalLingo = components["schemas"]["NonverbalLingoRead"];
export type NonverbalBatch = components["schemas"]["NonverbalBatchIn"];

export function readNonverbal(attemptId: string, signal?: AbortSignal): Promise<NonverbalRead> {
  return platformRequest(`/api/v1/attempts/${encodeURIComponent(attemptId)}/nonverbal`, { signal });
}

export function postNonverbalBatch(attemptId: string, body: NonverbalBatch): Promise<unknown> {
  return platformRequest(`/api/v1/attempts/${encodeURIComponent(attemptId)}/nonverbal-batches`, {
    method: "POST",
    body,
  });
}

/** Turn cues on (with the wording version shown) or off; the api ignores the version on withdrawal and deletes what it stored. */
export function setNonverbalConsent(consented: boolean, version = ""): Promise<NonverbalRead> {
  return platformRequest("/api/v1/me/nonverbal-consent", { method: "PUT", body: { consented, version } });
}
