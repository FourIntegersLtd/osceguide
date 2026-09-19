"use client";

import { useCallback, useMemo, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, PageHeader, Spinner, cn } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { readResult } from "@/capabilities/attempt-runner";
import { FeedbackView, normaliseFeedback, RAG_LABEL, type Rag } from "@/capabilities/feedback";
import { readMyReview, saveReview } from "@/domains/assess/api";

const GRADES: Rag[] = ["R", "A", "G"];

/**
 * A supervisor's marking, beside the machine's.
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
  const state = useAsync(
    async (signal) => {
      const [result, mine] = await Promise.all([
        attemptId ? readResult(attemptId, signal).catch(() => null) : Promise.resolve(null),
        readMyReview(orgSlug, slotId, signal).catch(() => null),
      ]);
      return { result, mine };
    },
    [orgSlug, slotId, attemptId],
  );

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Mark this station" description="Your judgement, beside the machine's." />
      <AsyncBoundary state={state}>
        {(data) => (
          <Editor
            orgSlug={orgSlug}
            slotId={slotId}
            payload={data.result?.payload ?? null}
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
  payload,
  initial,
  onSaved,
}: {
  orgSlug: string;
  slotId: string;
  payload: Record<string, unknown> | null;
  initial: { field_values: Record<string, unknown>; notes: string | null; status: string } | null;
  onSaved: () => void;
}) {
  const domains = useMemo(
    () => (payload ? normaliseFeedback(payload).groups.map((group) => ({ key: group.key, label: group.label, machine: group.score })) : []),
    [payload],
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
  const [busy, setBusy] = useState<"draft" | "submitted" | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const submitted = initial?.status === "submitted";

  const persist = useCallback(
    async (status: "draft" | "submitted") => {
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
                <Button onClick={() => void persist("submitted")} disabled={busy !== null}>
                  {busy === "submitted" ? <Spinner /> : "Submit review"}
                </Button>
              </div>
            )}
          </div>
        </Card>
      </div>

      <div>
        {payload ? (
          <FeedbackView payload={payload} />
        ) : (
          <Card>
            <p className="text-sm text-ink-muted">
              No machine marking for this attempt yet. It appears here when scoring finishes.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
