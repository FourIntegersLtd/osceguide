"use client";

import { useSearchParams } from "next/navigation";
import { useSurface } from "@/capabilities";
import { useAuthoringScope } from "@/capabilities/authoring/parts/useAuthoringScope";
import { examResumePath } from "@/capabilities/authoring/templates/paths";

/** The New exam sheet that sent the author here (`?exam=<id>`), and the way back to it. */
export function useExamReturn(): { examId: string | null; examHref: string | null } {
  const { hrefFor } = useSurface();
  const scope = useAuthoringScope();
  const param = useSearchParams().get("exam");
  // The staff surface has no exams, so there is nothing to return to there.
  const examId = scope.kind === "org" ? param : null;
  return { examId, examHref: examId ? examResumePath(hrefFor, examId) : null };
}
