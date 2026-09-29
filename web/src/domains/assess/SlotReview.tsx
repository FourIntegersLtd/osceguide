"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { latestResult, readResults } from "@/capabilities/attempt-runner";
import { FeedbackView, normaliseFeedback, RAG_LABEL, type Rag } from "@/capabilities/feedback";
import { AttemptTranscript } from "@/domains/assess/AttemptTranscript";
import { readMySlotReview, saveReview } from "@/domains/assess/api";
import { GpLeadReview, SlotReviewers, readSlotReviews } from "@/domains/assess/results";
import type { SlotReviews } from "@/domains/assess/results";

const GRADES: Rag[] = ["R", "A", "G"];

/**
 * A station, marked three ways.
 *
 * An observer's own review, the lead's authoritative one, and what everybody
 * who watched agreed — beside the machine's marking. The retiring client had
 * the first of those and the platform had no screen for the other two at all,
 * so a GP lead's review existed on the backend and nothing could write one.
 *
 * The domains to score are derived from the feedback the engine actually
 * produced for this attempt, not from a list held here — which is how the old
 * client handled it and is the right answer while a sitting's template narrows
 * the platform schema rather than replacing it. The backend refuses a submit
 * that has not scored what the bound template requires, so that rule is not
 * re-implemented in the browser.
 */
export function SlotReview({
  orgSlug,
  slotId,
  attemptId,
}: {
  orgSlug: string;
  slotId: string;
  attemptId: string | null;
}) {
  /*
   * My review is read directly (`GET .../reviews/mine`). An earlier version
   * called that route before it existed, answered 405 on every load and
   * swallowed it, so a reviewer's own draft never came back. Where the route
   * is still not deployed, mine is the one in the slot's list with my id on
   * it; any other failure is a failure, not "no review".
   */
  const { session } = useSession();
  const userId = session?.user.id ?? null;

  const state = useAsync(
    async (signal) => {
      const [result, reviews, mine] = await Promise.all([
        attemptId
          ? readResults(attemptId, signal)
              .then(latestResult)
              .catch(() => null)
          : Promise.resolve(null),
        readSlotReviews(orgSlug, slotId, signal),
        readMySlotReview(orgSlug, slotId, signal),
      ]);
      return {
        result,
        reviews,
        mine:
          mine !== undefined
            ? mine
            : ((reviews.items ?? []).find((item) => item.submitted_by === userId) ?? null),
      };
    },
    [orgSlug, slotId, attemptId, userId],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mark this station" description="Your judgement, beside the machine's." />
      {attemptId ? null : (
        /*
         * Without an attempt there is no engine marking to derive the domains
         * from, and an empty list of domains reads as "this station has no
         * rubric" rather than as "this candidate was never dispatched". Say
         * which of the two it is.
         */
        <Alert tone="warning">
          This slot has no consultation on record, so there is nothing to mark against yet.
        </Alert>
      )}
      <AsyncBoundary state={state}>
        {(data) => (
          <Editor
            orgSlug={orgSlug}
            slotId={slotId}
            attemptId={attemptId}
            payload={data.result?.payload ?? null}
            reviews={data.reviews}
            initial={data.mine}
            onSaved={state.reload}
          />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Editor({
  orgSlug,
  slotId,
  attemptId,
  payload,
  reviews,
  initial,
  onSaved,
}: {
  orgSlug: string;
  slotId: string;
  attemptId: string | null;
  payload: Record<string, unknown> | null;
  reviews: SlotReviews;
  initial: { field_values: Record<string, unknown>; notes: string | null; status: string } | null;
  onSaved: () => void;
}) {
  /*
   * `.score` is not decoration: the backend only counts a field path that
   * ends in it (`domain.score` or `domain.skill.score`, see
   * `reviews/service.py`'s `_scored_domains`). A bare domain key here writes
   * a rating that scores, summaries and completion checks all silently
   * ignore.
   */
  const domains = useMemo(
    () =>
      payload
        ? normaliseFeedback(payload).groups.map((group) => ({
            key: `${group.key}.score`,
            label: group.label,
            machine: group.score,
          }))
        : [],
    [payload],
  );

  const labels = useMemo(
    () => Object.fromEntries(domains.map((domain) => [domain.key, domain.label])),
    [domains],
  );

  const [scores, setScores] = useState<Record<string, Rag>>(() => {
    const values = (initial?.field_values ?? {}) as Record<string, unknown>;
    const out: Record<string, Rag> = {};
    for (const [key, value] of Object.entries(values)) {
      if (value === "R" || value === "A" || value === "G") out[key] = value;
    }
    return out;
  });
  const [notes, setNotes] = useState(initial?.notes ?? "");
  const [busy, setBusy] = useState<"draft" | "completed" | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const submitted = initial?.status === "completed";

  const persist = useCallback(
    async (status: "draft" | "completed") => {
      setBusy(status);
      setError(null);
      try {
        await saveReview(orgSlug, slotId, { fieldValues: scores, notes: notes || null, status });
        setSaved(status === "draft" ? "Draft saved" : "Review submitted");
        onSaved();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(null);
      }
    },
    [orgSlug, slotId, scores, notes, onSaved],
  );

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <div className="flex flex-col gap-4">
        <Card
          title="Your marking"
          actions={submitted ? <Badge tone="success">Submitted</Badge> : <Badge tone="neutral">Draft</Badge>}
        >
          <div className="flex flex-col gap-4">
            {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
            {saved && !error && <Alert tone="success">{saved}</Alert>}

            {domains.length === 0 ? (
              <p className="text-sm text-ink-muted">
                The machine has not marked this attempt yet, so there are no domains to agree or
                disagree with. Your notes are still recorded.
              </p>
            ) : (
              <ul className="flex flex-col gap-3">
                {domains.map((domain) => (
                  <li key={domain.key} className="flex flex-col gap-1.5">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-ink">{domain.label}</span>
                      {domain.machine && (
                        <span className="text-xs text-ink-subtle">
                          machine: {RAG_LABEL[domain.machine]}
                        </span>
                      )}
                    </div>
                    <div className="flex gap-1.5" role="group" aria-label={domain.label}>
                      {GRADES.map((grade) => (
                        <button
                          key={grade}
                          type="button"
                          disabled={submitted}
                          aria-pressed={scores[domain.key] === grade}
                          onClick={() => setScores((current) => ({ ...current, [domain.key]: grade }))}
                          className={cn(
                            "flex-1 rounded-control border px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-60",
                            scores[domain.key] === grade
                              ? "border-accent bg-accent text-ink-inverse"
                              : "border-border-strong bg-surface text-ink-muted hover:text-ink",
                          )}
                        >
                          {RAG_LABEL[grade]}
                        </button>
                      ))}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium text-ink">Notes</span>
              <textarea
                rows={5}
                value={notes}
                disabled={submitted}
                onChange={(event) => setNotes(event.target.value)}
                className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm text-ink disabled:bg-surface-raised"
                placeholder="What you saw, in the words you would say to them."
              />
            </label>

            {!submitted && (
              <div className="flex justify-end gap-2">
                <Button variant="secondary" onClick={() => void persist("draft")} disabled={busy !== null}>
                  {busy === "draft" ? <Spinner /> : "Save draft"}
                </Button>
                <Button onClick={() => void persist("completed")} disabled={busy !== null}>
                  {busy === "completed" ? <Spinner /> : "Submit review"}
                </Button>
              </div>
            )}
          </div>
        </Card>

        {/* The lead's review is one per station and the observers' are one
            each, so they are separate panels rather than tabs of the same
            thing — a reviewer should be able to see both at once. */}
        <Card title="The lead's review" description="One per station, and the one that counts.">
          <GpLeadReview orgSlug={orgSlug} slotId={slotId} domains={domains} />
        </Card>

        <Card title="What the reviewers agreed">
          <SlotReviewers reviews={reviews} labelFor={(key: string) => labels[key] ?? key} />
        </Card>
      </div>

      <div className="flex flex-col gap-4">
        {payload ? (
          <FeedbackView payload={payload} />
        ) : (
          <Card>
            <p className="text-sm text-ink-muted">
              No machine marking for this attempt yet. It appears here when scoring finishes.
            </p>
          </Card>
        )}
        {/* The marking is the machine's reading of the consultation; this is
            the consultation. A marker is asked to agree or disagree with the
            first, which is not a judgement they can make from a score alone. */}
        <AttemptTranscript attemptId={attemptId} />
      </div>
    </div>
  );
}
