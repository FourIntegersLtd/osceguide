import { platformRequest, type components } from "@/foundation/platform-client";
import { orgPath } from "@/domains/assess/api";

export type SittingReport = components["schemas"]["SittingReport"];
export type CandidateReport = components["schemas"]["CandidateReport"];
export type StationReport = components["schemas"]["StationReport"];
export type CohortSummary = components["schemas"]["CohortSummary"];
export type CohortCandidate = components["schemas"]["CohortCandidate"];
export type Decision = components["schemas"]["DecisionRead"];
export type GpLeadReview = components["schemas"]["GpLeadReviewRead"];
export type SlotReviews = components["schemas"]["SlotReviewsRead"];

/** What a decision was made against, sent so the backend can tell if it moved. */
export type Evidence = Record<string, unknown>;

export function readSittingReport(
  slug: string,
  sittingId: string,
  signal?: AbortSignal,
): Promise<SittingReport> {
  return platformRequest<SittingReport>(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/report`,
    { signal },
  );
}

/**
 * How this sitting's candidates compare, ranked.
 *
 * Exam sittings only — a training circuit is people practising, and ranking
 * them against each other would turn practice into an assessment nobody agreed
 * to sit. A training sitting answers 422 `not_an_exam_sitting`, which the
 * screen treats as "no ranking here" rather than as a failure.
 */
export function readCohort(
  slug: string,
  sittingId: string,
  signal?: AbortSignal,
): Promise<CohortSummary> {
  return platformRequest<CohortSummary>(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/cohort`,
    { signal },
  );
}

/* ------------------------------------------------------------------------
 * One candidate's decision: draft → signed off → released.
 *
 * Every save is a new revision and the table is append-only, so what was
 * previously considered survives and the record is still defensible months
 * later. `trainee_id` here is a roster id — not the user id a circuit slot
 * names, which is the other thing that word means on this backend.
 * --------------------------------------------------------------------- */

const decisionPath = (slug: string, sittingId: string, traineeId: string) =>
  `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/candidates/${encodeURIComponent(traineeId)}/decision`;

export function readDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
  signal?: AbortSignal,
): Promise<Decision> {
  return platformRequest<Decision>(decisionPath(slug, sittingId, traineeId), { signal });
}

/**
 * Save a draft.
 *
 * A PUT, and it was being sent as a POST — which 405s, so nothing recorded a
 * decision at all. `evidence` is the marking the outcome was judged against;
 * the backend fingerprints it at sign-off and re-checks it at release.
 */
export function saveDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
  input: { assessmentOutcome: string | null; rationale: string | null; evidence: Evidence },
): Promise<Decision> {
  return platformRequest<Decision>(decisionPath(slug, sittingId, traineeId), {
    method: "PUT",
    body: {
      assessment_outcome: input.assessmentOutcome,
      rationale: input.rationale,
      evidence: input.evidence,
    },
  });
}

export function signOffDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
): Promise<Decision> {
  return platformRequest<Decision>(`${decisionPath(slug, sittingId, traineeId)}/sign-off`, {
    method: "POST",
  });
}

/**
 * Release it to the candidate.
 *
 * The evidence goes up again, and the backend refuses the release if it no
 * longer matches what was signed off: a station re-marked in between would
 * otherwise send somebody an outcome nobody approved. Sending nothing made
 * that check compare two empty objects and always pass.
 */
export function releaseDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
  evidence: Evidence,
): Promise<Decision> {
  return platformRequest<Decision>(`${decisionPath(slug, sittingId, traineeId)}/release`, {
    method: "POST",
    body: { evidence },
  });
}

/* ---------- the GP lead's review of one station ---------- */

export function readGpLeadReview(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<GpLeadReview> {
  return platformRequest<GpLeadReview>(
    `${orgPath(slug)}/slots/${encodeURIComponent(slotId)}/gp-lead-review`,
    { signal },
  );
}

/**
 * Save it.
 *
 * `revision` is what this browser last read, and the backend refuses a save
 * against a stale one — so two leads with the same station open cannot
 * silently overwrite each other.
 */
export function saveGpLeadReview(
  slug: string,
  slotId: string,
  input: {
    revision: number;
    fieldValues: Record<string, unknown>;
    notes: string | null;
    overallRag: string | null;
    status: "draft" | "completed";
  },
): Promise<GpLeadReview> {
  return platformRequest<GpLeadReview>(
    `${orgPath(slug)}/slots/${encodeURIComponent(slotId)}/gp-lead-review`,
    {
      method: "PUT",
      body: {
        revision: input.revision,
        field_values: input.fieldValues,
        notes: input.notes,
        overall_rag: input.overallRag,
        status: input.status,
      },
    },
  );
}

/** Every review of one slot, and what they add up to. */
export function readSlotReviews(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<SlotReviews> {
  return platformRequest<SlotReviews>(
    `${orgPath(slug)}/slots/${encodeURIComponent(slotId)}/reviews`,
    { signal },
  );
}
