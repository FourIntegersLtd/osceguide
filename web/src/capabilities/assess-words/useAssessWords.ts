import { useOptionalSurface } from "@/capabilities/SurfaceContext";
import { assessWordsFor, type AssessWords } from "@/capabilities/assess-words/vocabulary";

/** The words for this workspace; see `assessWordsFor`. Safe outside a shell. */
export function useAssessWords(): AssessWords {
  return assessWordsFor(useOptionalSurface()?.surface);
}
