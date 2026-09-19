"use client";

import { useCallback, useState } from "react";
import { Alert, Badge, Button, Spinner, b2bTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { RAG_LABEL, type Rag } from "@/capabilities/feedback";
import { readGpLeadReview, saveGpLeadReview, type GpLeadReview as Review } from "@/domains/assess/results/api";

const GRADES: Rag[] = ["R", "A", "G"];

export interface ReviewDomain {
  key: string;
  label: string;
  machine?: Rag | null;
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
 * Nothing in the retiring client wired this at all.
 */
export function GpLeadReview({
  orgSlug,
  slotId,
  domains,
}: {
  orgSlug: string;
  slotId: string;
  domains: ReviewDomain[];
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

  return (
    <Editor
      key={state.data?.revision ?? 0}
      orgSlug={orgSlug}
      slotId={slotId}
      domains={domains}
      review={state.data}
      onSaved={state.reload}
    />
  );
}

function Editor({
  orgSlug,
  slotId,
  domains,
  review,
  onSaved,
}: {
  orgSlug: string;
  slotId: string;
  domains: ReviewDomain[];
  review: Review | null;
  onSaved: () => void;
}) {
  const [scores, setScores] = useState<Record<string, Rag>>(() => readScores(review));
  const [overall, setOverall] = useState<Rag | "">((review?.overall_rag as Rag) ?? "");
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
        await saveGpLeadReview(orgSlug, slotId, {
          revision: review?.revision ?? 0,
          fieldValues: scores,
          notes: notes.trim() || null,
          overallRag: overall || null,
          status,
        });
        setNote(status === "draft" ? "Draft saved." : "Review completed.");
        onSaved();
      } catch (cause) {
        // A conflict is not a failure to retry: somebody else's words are in
        // there now, and saving over them is exactly what this prevents.
        if (hasCode(cause, "review_conflict")) setStale(true);
        setFailure(errorMessage(cause instanceof Error ? cause : new Error(String(cause))));
      } finally {
        setBusy(null);
      }
    },
    [orgSlug, slotId, review, scores, notes, overall, onSaved],
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

      {domains.length === 0 ? (
        <p className="text-osce-body text-b2b-mid">
          This station has no marked domains yet, so there is nothing to agree or disagree with.
          Notes are still recorded.
        </p>
      ) : (
        <ul className="space-y-3">
          {domains.map((domain) => (
            <li key={domain.key} className="space-y-1.5">
              <div className="flex items-center justify-between gap-3">
                <span className="text-osce-caption font-medium text-b2b-headline">
                  {domain.label}
                </span>
                {domain.machine ? (
                  <span className="text-osce-caption text-b2b-mid">
                    machine: {RAG_LABEL[domain.machine]}
                  </span>
                ) : null}
              </div>
              <RagRow
                label={domain.label}
                value={scores[domain.key] ?? null}
                onPick={(grade) => setScores((current) => ({ ...current, [domain.key]: grade }))}
              />
            </li>
          ))}
        </ul>
      )}

      <div className="space-y-1.5">
        <span className="text-osce-caption font-medium text-b2b-headline">Overall</span>
        <RagRow label="Overall" value={overall || null} onPick={setOverall} />
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
        Completing needs every domain scored — a half-marked review shown to a candidate is worse
        than one openly still in progress.
      </p>
    </div>
  );
}

function RagRow({
  label,
  value,
  onPick,
}: {
  label: string;
  value: Rag | null;
  onPick: (grade: Rag) => void;
}) {
  return (
    <div className="flex gap-1.5" role="group" aria-label={label}>
      {GRADES.map((grade) => (
        <button
          key={grade}
          type="button"
          aria-pressed={value === grade}
          onClick={() => onPick(grade)}
          className={
            value === grade
              ? "flex-1 rounded-md border border-b2b-accent bg-b2b-accent px-3 py-1.5 text-osce-caption font-medium text-white"
              : "flex-1 rounded-md border border-b2b-border bg-white px-3 py-1.5 text-osce-caption font-medium text-b2b-mid hover:bg-b2b-cream"
          }
        >
          {RAG_LABEL[grade]}
        </button>
      ))}
    </div>
  );
}

function readScores(review: Review | null): Record<string, Rag> {
  const out: Record<string, Rag> = {};
  for (const [key, value] of Object.entries(review?.field_values ?? {})) {
    if (value === "R" || value === "A" || value === "G") out[key] = value;
  }
  return out;
}
