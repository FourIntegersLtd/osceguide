"use client";

import { useCallback, useState } from "react";
import { Alert, Badge, Button, Spinner, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
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

function asVerdict(value: string | null | undefined): Verdict | "" {
  return VERDICTS.find((verdict) => verdict.value === value)?.value ?? "";
}

/**
 * The lead's review of one station — the one that counts.
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
}: {
  orgSlug: string;
  slotId: string;
  /** The slot's review form, for a lead writing the first review. */
  form: ReviewForm | null;
  /** The machine's marked payload, shown beside each field. */
  payload: Record<string, unknown> | null;
}) {
  const state = useAsync(async (signal) => {
    try {
      return await readGpLeadReview(orgSlug, slotId, signal);
    } catch (cause) {
      // No review yet is the ordinary case. Revision zero is what the backend
      // expects from a first save.
      if (hasCode(cause, "review_not_found")) return null;
      throw cause;
    }
  }, [orgSlug, slotId]);

  if (state.loading) return <Spinner />;
  if (state.error) return <Alert tone="danger">{errorMessage(state.error)}</Alert>;

  // Loaded once. A save answers with the stored review, which the editor keeps;
  // reloading here would remount the editor and wipe its "saved" note (R-3).
  return <Editor orgSlug={orgSlug} slotId={slotId} form={form} payload={payload} loaded={state.data} />;
}

function Editor({
  orgSlug,
  slotId,
  form,
  payload,
  loaded,
}: {
  orgSlug: string;
  slotId: string;
  /** The slot's form, used until the review has one of its own. */
  form: ReviewForm | null;
  payload: Record<string, unknown> | null;
  /** The review as first read, or null before anyone has saved one. */
  loaded: Review | null;
}) {
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

  const save = useCallback(
    async (status: "draft" | "completed") => {
      setBusy(status);
      setFailure(null);
      setNote(null);
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
        if (hasCode(cause, "review_conflict")) setStale(true);
        setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
      } finally {
        setBusy(null);
      }
    },
    [orgSlug, slotId, review, ratings, comments, notes, overall],
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={completed ? "success" : "neutral"}>
          {completed ? "Completed" : "Draft"}
        </Badge>
        {review ? (
          <span className="text-osce-caption text-b2b-mid">Revision {review.revision}</span>
        ) : null}
      </div>

      {stale ? (
        <Alert tone="warning">
          Somebody else has changed this review since you opened it. Reload the page and apply your
          changes to theirs — saving over it is what this stops.
        </Alert>
      ) : failure ? (
        <Alert tone="danger">{failure}</Alert>
      ) : note ? (
        <Alert tone="success">{note}</Alert>
      ) : null}

      <ReviewFields
        form={review?.form ?? form}
        ratings={ratings}
        onRate={(path, value) => setRatings((current) => ({ ...current, [path]: value }))}
        payload={payload}
        comments={comments}
        onComment={(domainId, text) => setComments((current) => ({ ...current, [domainId]: text }))}
      />

      <div className="space-y-1.5">
        <span className="text-osce-caption font-medium text-b2b-headline">Overall</span>
        <VerdictRow value={overall || null} onPick={setOverall} />
      </div>

      <label className="block">
        <span className="text-osce-caption font-medium text-b2b-headline">Notes</span>
        <textarea
          rows={4}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          placeholder="What you saw, in the words you would say to them."
          className={`${b2bTokens.b2bInputBase} mt-1 w-full`}
        />
      </label>

      <div className="flex flex-wrap justify-end gap-2">
        <Button
          themeType="b2b"
          variant="secondary"
          isLoading={busy === "draft"}
          disabled={busy !== null}
          onClick={() => void save("draft")}
        >
          Save draft
        </Button>
        <Button
          themeType="b2b"
          variant="commit"
          isLoading={busy === "completed"}
          disabled={busy !== null}
          onClick={() => void save("completed")}
        >
          {completed ? "Save changes" : "Complete review"}
        </Button>
      </div>

      <p className="text-osce-caption text-b2b-mid">
        Completing needs every required domain rated — a half-marked review shown to a candidate is worse
        than one openly still in progress.
      </p>
    </div>
  );
}

function VerdictRow({ value, onPick }: { value: Verdict | null; onPick: (verdict: Verdict) => void }) {
  return (
    <div className="flex gap-1.5" role="group" aria-label="Overall">
      {VERDICTS.map((verdict) => (
        <button
          key={verdict.value}
          type="button"
          aria-pressed={value === verdict.value}
          onClick={() => onPick(verdict.value)}
          className={
            value === verdict.value
              ? "flex-1 rounded-md border border-b2b-accent bg-b2b-accent px-3 py-1.5 text-osce-caption font-medium text-white"
              : "flex-1 rounded-md border border-b2b-border bg-white px-3 py-1.5 text-osce-caption font-medium text-b2b-mid hover:bg-b2b-cream"
          }
        >
          {verdict.label}
        </button>
      ))}
    </div>
  );
}
