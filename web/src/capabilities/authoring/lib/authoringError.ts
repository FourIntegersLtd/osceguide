import { errorMessage } from "@/foundation/hooks";
import { isPlatformError } from "@/foundation/platform-client";
import { INSTITUTION_WORDS, type AssessWords } from "@/capabilities/assess-words/vocabulary";
import { examRefusalMessage } from "@/capabilities/authoring/lib/authoringCopy";

/** What an authoring failure says: the arm's plain words for a known refusal, else the server's message. */
export function authoringErrorMessage(cause: unknown, w: AssessWords = INSTITUTION_WORDS): string {
  return (isPlatformError(cause) ? examRefusalMessage(cause.code, w) : null) ?? errorMessage(cause);
}
