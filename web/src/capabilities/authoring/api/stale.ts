import { hasCode } from "@/foundation/platform-client";

/**
 * The refusal an editor shows when someone else saved first (B-15), or null for any other failure.
 *
 * Branches on the code, never the server's English. The caller reloads what it was editing before
 * it throws this, so the words are true by the time they are read.
 */
export function staleRefusal(cause: unknown, what: string): Error | null {
  if (!hasCode(cause, "stale_revision")) return null;
  return new Error(
    `Someone else changed this ${what} just now. We have reloaded it with their changes; your changes were not saved. Please make your edit again.`,
  );
}
