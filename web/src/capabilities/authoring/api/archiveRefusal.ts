import { PlatformError, hasCode } from "@/foundation/platform-client";
import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

/** A count from an error's `details`, or 0 when the server sent none. */
function count(details: Record<string, unknown> | null, key: string): number {
  const value = details?.[key];
  return typeof value === "number" ? value : 0;
}

/**
 * An archive the server refused because the station is still in use, restated in plain words
 * (still a `PlatformError`, so screens show its message). Any other failure comes back unchanged.
 */
export function explainArchiveRefusal(cause: unknown, w: AssessWords): unknown {
  if (!hasCode(cause, "not_archivable") || cause.details?.reason !== "in_use") return cause;
  const circuits = count(cause.details, "circuits");
  const sets = count(cause.details, "sets");
  return new PlatformError(cause.status, {
    code: cause.code,
    message: !w.hiring
      ? `This station is on ${circuits} unfinished circuit(s) and ${sets} practice set(s). Take it off those first, or publish a new version.`
      : `This station is still in ${circuits} unfinished ${circuits === 1 ? w.circuit : w.circuits} and ${sets} practice ${sets === 1 ? "set" : "sets"}. Remove it from those, or publish a new version, then archive it.`,
    details: cause.details,
    request_id: cause.requestId ?? undefined,
  });
}
