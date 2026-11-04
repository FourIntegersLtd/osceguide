import { useOptionalSurface } from "@/capabilities";
import { assessWordsFor, type AssessWords } from "@/domains/assess/vocabulary";

/** The words for this workspace; see `assessWordsFor`. Safe outside a shell. */
export function useAssessWords(): AssessWords {
  return assessWordsFor(useOptionalSurface()?.surface);
}
