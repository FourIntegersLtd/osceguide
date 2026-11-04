import { PlatformError, hasCode } from "@/foundation/platform-client";

/** A count from an error's `details`, or 0 when the server sent none. */
function count(details: Record<string, unknown> | null, key: string): number {
  const value = details?.[key];
  return typeof value === "number" ? value : 0;
}

/**
 * An archive the server refused because the station is still in use, restated in plain words
 * (still a `PlatformError`, so screens show its message). Any other failure comes back unchanged.
 */
export function explainArchiveRefusal(cause: unknown): unknown {
  if (!hasCode(cause, "not_archivable") || cause.details?.reason !== "in_use") return cause;
  const circuits = count(cause.details, "circuits");
  const sets = count(cause.details, "sets");
  return new PlatformError(cause.status, {
    code: cause.code,
    message: `This station is on ${circuits} unfinished circuit(s) and ${sets} practice set(s). Take it off those first, or publish a new version.`,
    details: cause.details,
    request_id: cause.requestId ?? undefined,
  });
}
