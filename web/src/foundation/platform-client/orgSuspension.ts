import type { PlatformErrorCode } from "@/foundation/platform-client/errors";

/**
 * Which organisations platform-api has said are suspended, this page load.
 *
 * `require_org` refuses every org route of a suspended organisation with
 * `organization_suspended`, and the membership list does not carry the
 * organisation's status, so the first refused request is the only place the
 * web learns it. Each panel used to show its own raw 403 (F-1); the client
 * notes the refusal here and the workspace frame swaps the whole shell for one
 * screen. A slug leaves the set only on a reload: restoring an organisation is
 * rare, and reloading is what the screen asks for.
 */

const suspended = new Set<string>();
const listeners = new Set<() => void>();

const ORG_PATH = /^\/api\/v1\/orgs\/([^/?#]+)/;

/** Called for every refused request; does nothing unless it is a suspension
 *  of the organisation the path names. */
export function noteOrgRefusal(path: string, code: PlatformErrorCode): void {
  if (code !== "organization_suspended") return;
  const slug = ORG_PATH.exec(path)?.[1];
  if (slug) markOrgSuspended(decodeURIComponent(slug));
}

/** Record that platform-api refused this organisation as suspended, for a
 *  refusal whose path does not name it (switching workspace). */
export function markOrgSuspended(slug: string): void {
  if (suspended.has(slug)) return;
  suspended.add(slug);
  for (const listener of listeners) listener();
}

export function isOrgSuspended(slug: string): boolean {
  return suspended.has(slug);
}

/** Forget every suspension, as a reload does. For tests. */
export function resetOrgSuspension(): void {
  suspended.clear();
}

/** For `useSyncExternalStore`. */
export function subscribeOrgSuspension(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
