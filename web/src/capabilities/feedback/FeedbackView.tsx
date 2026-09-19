"use client";

import { useMemo } from "react";
import { HiOutlineFaceFrown } from "react-icons/hi2";
import { B2CEmptyState } from "@/foundation/ui";
import { normaliseFeedback } from "@/capabilities/feedback/model";
import { FeedbackDomains } from "@/capabilities/feedback/FeedbackDomains";
import { FeedbackCategories } from "@/capabilities/feedback/FeedbackCategories";
import { FeedbackClinicalAnalysis } from "@/capabilities/feedback/FeedbackClinicalAnalysis";
import { FeedbackLiveCoverage } from "@/capabilities/feedback/FeedbackLiveCoverage";
import { FeedbackPriorityAreas } from "@/capabilities/feedback/FeedbackPriorityAreas";

/**
 * One scored attempt, rendered.
 *
 * The same component shows a consumer their practice feedback and an examiner
 * the machine's view of a candidate's — the sections, their order and their
 * wording are the retiring consumer screen's, and nothing here asks who is
 * reading. A reviewer's controls are composed around this rather than forking
 * it; two renderers is how the two clients came to disagree about what a grade
 * meant.
 *
 * `payload` is the assessment result's payload exactly as the engine wrote it.
 * Everything framework-specific about reading it lives in `model.ts`, so the
 * four exams — and the fifth nobody has written yet — come through here.
 */
export function FeedbackView({
  payload,
  className = "space-y-8",
}: {
  payload: Record<string, unknown>;
  className?: string;
}) {
  const feedback = useMemo(() => normaliseFeedback(payload), [payload]);
  const isEmpty =
    feedback.groups.length === 0 &&
    feedback.priorities.length === 0 &&
    feedback.analysis.length === 0 &&
    feedback.coverage.length === 0;

  if (isEmpty) {
    return (
      <B2CEmptyState
        icon={HiOutlineFaceFrown}
        title="No feedback recorded"
        description="This attempt has no feedback recorded. If it was just completed, scoring may still be running."
      />
    );
  }

  return (
    <section className={className}>
      <FeedbackDomains groups={feedback.groups} />
      <FeedbackCategories groups={feedback.groups} />
      <FeedbackClinicalAnalysis sections={feedback.analysis} />
      <FeedbackLiveCoverage coverage={feedback.coverage} />
      <FeedbackPriorityAreas priorities={feedback.priorities} />
    </section>
  );
}
