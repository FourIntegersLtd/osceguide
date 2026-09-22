import { platformRequest, type components } from "@/foundation/platform-client";

/**
 * What the public marketing site asks the backend.
 *
 * Both routes are unauthenticated on purpose — a landing page is what a
 * visitor sees before anything else — so nothing here may assume a session.
 */

export type SiteStatistics = components["schemas"]["SiteStatistics"];

/**
 * The counters for the landing page's numbers band.
 *
 * `GET /site/statistics` replaced the retiring backend's `/api/landing`. It is
 * cached for ten minutes server-side and carries `as_of`, the moment the
 * figures were counted, so a client can say "as of" rather than implying the
 * numbers are live.
 */
export function readSiteStatistics(signal?: AbortSignal): Promise<SiteStatistics> {
  return platformRequest<SiteStatistics>("/api/v1/site/statistics", { signal });
}
