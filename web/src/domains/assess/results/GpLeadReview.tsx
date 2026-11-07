"use client";

import { boardChip, boardInput, boardLabel, boardSeg, boardSegChoice , boardBtn, boardAlert } from "@/foundation/ui/boardKit";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Spinner, b2bTokens } from "@/foundation/ui";

import { errorMessage, useAsync } from "@/foundation/hooks";
import { assessErrorMessage } from "@/domains/assess/errorCopy";
import { hasCode } from "@/foundation/platform-client";
import type { RatingValue } from "@/capabilities/feedback/rubric";
import { readGpLeadReview, saveGpLeadReview, type GpLeadReview as Review } from "@/domains/assess/results/api";
import { ReviewFields } from "@/domains/assess/results/ReviewFields";
import {
  fieldValuesFor,
  initialComments,
  leadSaveNote,
  initialRatings,
  type ReviewForm,
} from "@/domains/assess/results/reviewForm";
import { useAssessWords } from "@/domains/assess/useAssessWords";

/**
 * The lead's overall verdict. Unlike the per-domain ratings, which take
 * whatever the rubric rates in, this is always green, amber or red: the
 * backend stores it as one of the three letters for every exam.
 */
const VERDICTS = [
  { value: "G", label: "Green" },
  { value: "A", label: "Amber" },
  { value: "R", label: "Red" },
] as const;
type Verdict = (typeof VERDICTS)[number]["value"];
const TONE = { G: "success", A: "warning", R: "danger" } as const;

function asVerdict(value: string | null | undefined): Verdict | "" {
  return VERDICTS.find((verdict) => verdict.value === value)?.value ?? "";
}

/**
 * The admin's review of one station — the one that counts.
 *
 * Distinct from the observers' reviews beside it: there are as many of those
 * as there were people watching, and exactly one of these. It is revisioned,
 * and a save carries the revision this browser read, so two leads with the
 * same station open cannot silently overwrite each other — the second is told
 * to reload rather than quietly winning.
 *
 * The fields to rate come from the rubric (`ReviewFormRead`): the review's
 * own form once one exists, else the slot's, which is what the screen passes
 * in for a first review. Each domain has its own note, stored beside the
 * ratings as `<domain>.comment`. Autosave and an AI prefill are not here: a
 * lead still saves when they mean to, and the machine's rating is shown at
 * each field so they can agree or disagree with it.
 */
export function GpLeadReview({
  orgSlug,
  slotId,
  form,
  payload,
  onStatus,
}: {
  orgSlug: string;
  slotId: string;
  /** Told the stored review's status once read and after each save, for the screen's steps. */
  onStatus?: (status: string | null) => void;
  /** The slot's review form, for a lead writing the first review. */
  form: ReviewForm | null;
  /** The machine's marked payload, shown beside each field. */
  payload: Record<string, unknown> | null;
}) {
  // `null` (no review yet) is the ordinary case; the editor then saves revision zero.
  const state = useAsync((signal) => readGpLeadReview(orgSlug, slotId, signal), [orgSlug, slotId]);

  if (state.loading) return <><LeadHeading /><Spinner /></>;
  if (state.error) return <><LeadHeading /><div role="alert" className={boardAlert("bad")}>{errorMessage(state.error)}</div></>;

  // Loaded once. A save answers with the stored review, which the editor keeps;
  // reloading here would remount the editor and wipe its "saved" note (R-3).
  return (
    <Editor orgSlug={orgSlug} slotId={slotId} form={form} payload={payload} loaded={state.data} onStatus={onStatus} />
  );
}

function Editor({
  orgSlug,
  slotId,
  form,
  payload,
  loaded,
  onStatus,
}: {
  orgSlug: string;
  slotId: string;
  onStatus?: (status: string | null) => void;
  /** The slot's form, used until the review has one of its own. */
  form: ReviewForm | null;
  payload: Record<string, unknown> | null;
  /** The review as first read, or null before anyone has saved one. */
  loaded: Review | null;
}) {
  const w = useAssessWords();
  // The latest stored review: what was read, then each save's answer. Its
  // revision is what the next save must carry.
  const [review, setReview] = useState<Review | null>(loaded);
  const [ratings, setRatings] = useState<Record<string, RatingValue>>(() =>
    initialRatings(loaded?.form ?? form, loaded?.field_values),
  );
  const [comments, setComments] = useState<Record<string, string>>(() =>
    initialComments(loaded?.form ?? form, loaded?.field_values),
  );
  const [overall, setOverall] = useState<Verdict | "">(asVerdict(review?.overall_rag));
  const [notes, setNotes] = useState(review?.notes ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  const completed = review?.status === "completed";
  const status = review?.status ?? null;
  useEffect(() => onStatus?.(status), [onStatus, status]);

  const save = useCallback(
    async (status: "draft" | "completed") => {
      setBusy(status);
      setFailure(null);
      setNote(null);
      setStale(false);
      try {
        const saved = await saveGpLeadReview(orgSlug, slotId, {
          revision: review?.revision ?? 0,
          fieldValues: fieldValuesFor(ratings, comments),
          notes: notes.trim() || null,
          overallRag: overall || null,
          status,
        });
        setReview(saved);
        setNote(leadSaveNote(saved.status));
      } catch (cause) {
        // A conflict is not a failure to retry: somebody else's words are in
        // there now, and saving over them is exactly what this prevents.
        setStale(hasCode(cause, "review_conflict"));
        setFailure(assessErrorMessage(cause, w));
      } finally {
        setBusy(null);
      }
    },
    [orgSlug, slotId, review, ratings, comments, notes, overall],
  );

  return (
    <>
      <LeadHeading
        status={
          <span className="text-assess-meta text-osce-ink-500">
            <span className={boardChip(completed ? "ok" : "neutral")}>{completed ? "Completed" : "Draft"}</span>
            {review ? ` Revision ${review.revision}` : null}
          </span>
        }
      />

      {failure ? (
        <div role="alert" className={boardAlert(stale ? "warn" : "bad")}>{failure}</div>
      ) : note ? (
        <div role="status" className={boardAlert("ok")}>{note}</div>
      ) : null}

      <ReviewFields
        form={review?.form ?? form}
        ratings={ratings}
        onRate={(path, value) => setRatings((current) => ({ ...current, [path]: value }))}
        payload={payload}
        comments={comments}
        onComment={(domainId, text) => setComments((current) => ({ ...current, [domainId]: text }))}
      />

      <div>
        <span className={`${boardLabel} !mb-2`}>Overall</span>
        <VerdictRow value={overall || null} onPick={setOverall} />
      </div>

      <label className="block">
        <span className={`${boardLabel} !mb-2`}>Notes</span>
        <textarea
          rows={4}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="What you saw, in the words you would say to them."
          className={`${boardInput} min-h-24 py-2.5`}
        />
      </label>

      <div className="flex flex-wrap items-center gap-2.5">
        <button type="button" className={boardBtn()} disabled={busy !== null} onClick={() => save("draft")}>
          {busy === "draft" ? <Spinner className="text-current" /> : "Save draft"}
        </button>
        <button type="button" className={boardBtn("primary")} disabled={busy !== null} onClick={() => save("completed")}>
          {busy === "completed" ? <Spinner className="text-current" /> : completed ? "Save changes" : "Complete review"}
        </button>
      </div>

      <div className={b2bTokens.assessMeta}>
        Rate every required area before completing the review, so candidates never see a half-finished one. A completed admin review stays editable (Save changes).
      </div>
    </>
  );
}

/** The card's title row and its one-line purpose, drawn in every state of the form. */
function LeadHeading({ status }: { status?: ReactNode }) {
  return (
    <>
      <div className="flex flex-wrap justify-between gap-3">
        <h2 className="text-base font-semibold leading-normal">Admin&apos;s review</h2>
        {status}
      </div>
      <div className={b2bTokens.assessMeta}>One overall mark for the station. This is the mark that counts.</div>
    </>
  );
}

function VerdictRow({ value, onPick }: { value: Verdict | null; onPick: (verdict: Verdict) => void }) {
  return (
    <div className={boardSeg} role="group" aria-label="Overall">
      {VERDICTS.map((verdict) => (
        <button
          key={verdict.value}
          type="button"
          aria-pressed={value === verdict.value}
          onClick={() => onPick(verdict.value)}
          className={boardSegChoice(value === verdict.value, TONE[verdict.value])}
        >
          {verdict.label}
        </button>
      ))}
    </div>
  );
}
