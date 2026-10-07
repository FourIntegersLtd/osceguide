import { hasCode } from "@/foundation/platform-client";

/** A refused adoption said in plain words, or null for a failure that is not a refusal. */
export function adoptRefusal(cause: unknown): string | null {
  if (hasCode(cause, "exam_already_imported")) return "Your organisation already runs that exam. It is in your programmes below.";
  if (hasCode(cause, "unknown_exam")) return "The platform no longer offers that exam. The list has been refreshed.";
  return null;
}
