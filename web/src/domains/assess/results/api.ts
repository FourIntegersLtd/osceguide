import {
  platformDownload,
  platformRequest,
  type PlatformDownload,
  type components,
} from "@/foundation/platform-client";
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

/** The sitting report as a CSV file the browser saves. */
export function downloadSittingResults(slug: string, sittingId: string): Promise<PlatformDownload> {
  return platformDownload(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/report.csv`,
  );
}

/**
 * One candidate's released result as a PDF.
 *
 * `traineeId` is the roster id. The route refuses a decision that has not
 * been released, which is why the button is only offered once it has.
 */
export function downloadCandidateResult(
  slug: string,
  sittingId: string,
  traineeId: string,
): Promise<PlatformDownload> {
  return platformDownload(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/candidates/${encodeURIComponent(traineeId)}/result.pdf`,
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

export type SittingReadout = components["schemas"]["SittingReadout"];

/**
 * The examination's read-out, as one document.
 *
 * The head of it (who sat what, the cohort's counts), the candidates in review
 * order, what to do about them, and the method that produced all three — the
 * thing an external reviewer is handed. Exam sittings only: a training sitting
 * answers 422 `not_an_exam_sitting`, which the caller treats as "there is no
 * read-out here" rather than as a failure, exactly as the cohort screen already
 * does with the same refusal.
 *
 * Served as JSON, and the retiring client's markdown file was rendered from
 * that same document server-side. Nothing here uploads it anywhere: it is
 * fetched and written to a file in the browser.
 */
export function readSittingReadout(
  slug: string,
  sittingId: string,
  signal?: AbortSignal,
): Promise<SittingReadout> {
  return platformRequest<SittingReadout>(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/readout`,
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
): Promise<Decision | null> {
  // `null` until a draft is recorded: the ordinary state, not an error.
  return platformRequest<Decision | null>(decisionPath(slug, sittingId, traineeId), { signal });
}

/**
 * Save a draft.
 *
 * A PUT, and it was being sent as a POST — which 405s, so nothing recorded a
 * decision at all. The backend reads the marking the outcome is judged
 * against itself, fingerprints it at sign-off and re-checks it at release.
 *
 * `expectedRevision` is the revision this screen last read, or 0 when it read
 * nothing. The table is append-only, so a stale save looked harmless and was
 * not: two administrators each saw "Revision 2" about different words, and the
 * draft that reached sign-off was whichever request landed last. The backend
 * refuses it with 409 `decision_revised`.
 */
export function saveDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
  input: {
    assessmentOutcome: string | null;
    /** Only an exam-mode sitting takes one; the server refuses it on a training sitting. */
    recruitmentOutcome: string | null;
    rationale: string | null;
    expectedRevision: number;
  },
): Promise<Decision> {
  return platformRequest<Decision>(decisionPath(slug, sittingId, traineeId), {
    method: "PUT",
    body: {
      assessment_outcome: input.assessmentOutcome,
      recruitment_outcome: input.recruitmentOutcome,
      rationale: input.rationale,
      expected_revision: input.expectedRevision,
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

export function releaseDecision(
  slug: string,
  sittingId: string,
  traineeId: string,
): Promise<Decision> {
  return platformRequest<Decision>(`${decisionPath(slug, sittingId, traineeId)}/release`, {
    method: "POST",
  });
}

export type BulkReleaseResult = components["schemas"]["BulkReleaseResult"];

/**
 * Release several candidates' decisions in one request.
 *
 * The backend loops them through the single release, so each keeps its own
 * server-side evidence re-check and its own `candidate_result_released` email, and a
 * refused candidate comes back under `skipped` with its code rather than
 * failing the rest.
 */
export function releaseDecisions(
  slug: string,
  sittingId: string,
  candidates: { traineeId: string }[],
): Promise<BulkReleaseResult> {
  return platformRequest<BulkReleaseResult>(
    `${orgPath(slug)}/sittings/${encodeURIComponent(sittingId)}/decisions/release`,
    {
      method: "POST",
      body: {
        candidates: candidates.map((candidate) => ({ trainee_id: candidate.traineeId })),
      },
    },
  );
}

/* ---------- the GP lead's review of one station ---------- */

export function readGpLeadReview(
  slug: string,
  slotId: string,
  signal?: AbortSignal,
): Promise<GpLeadReview | null> {
  // `null` until the lead's first save.
  return platformRequest<GpLeadReview | null>(
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
