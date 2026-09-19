"use client";

import { useState } from "react";
import { HiCheckCircle } from "react-icons/hi2";
import { Alert, Button, b2bTokens } from "@/foundation/ui";
import { finalizeCircuitReview } from "@/domains/assess/sessions/api";
import type { CircuitConsole } from "@/domains/assess/sessions/api";

/**
 * Publishing what was marked, once the circuit is done.
 *
 * The retiring runner counted saved feedback by probing one request per slot;
 * the console frame already says which stations have been marked, so the count
 * is read rather than asked for. Publishing stays off until at least one has
 * been, which is the same rule the old card enforced.
 *
 * There is no read for whether this has already been published — see
 * `docs/port-gaps.md` — so the card says what it did rather than what is true.
 */
export function CircuitFeedbackCard({
  data,
  orgSlug,
  circuitId,
  busy,
  run,
}: {
  data: CircuitConsole;
  orgSlug: string;
  circuitId: string;
  busy: string | null;
  run: (name: string, action: () => Promise<unknown>) => Promise<void>;
}) {
  const [notes, setNotes] = useState("");
  const [published, setPublished] = useState(false);
  const slots = data.slots ?? [];
  const marked = slots.filter((slot) => slot.has_review).length;

  if (slots.length === 0) return null;

  async function publish() {
    await run("publish", () => finalizeCircuitReview(orgSlug, circuitId, notes.trim() || null));
    setPublished(true);
  }

  return (
    <section className="space-y-3 rounded-lg border border-b2b-border bg-white p-4 sm:p-5">
      <h2 className={b2bTokens.b2bSectionTitle}>Share this circuit&apos;s feedback</h2>
      <p className="text-osce-body text-b2b-mid">
        Publishes one summary from everything marked across this circuit. Candidates read it as
        their circuit feedback; publishing again after an edit replaces it.
      </p>
      <p className="text-osce-caption font-medium text-b2b-headline">
        Marked on {marked} of {slots.length} station{slots.length === 1 ? "" : "s"}
      </p>

      <textarea
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
        rows={3}
        placeholder="Anything to say about the circuit as a whole (optional)"
        className={`${b2bTokens.b2bInputBase} w-full`}
      />

      {published ? <Alert tone="success">The circuit&apos;s feedback has been published.</Alert> : null}

      {marked === 0 ? (
        <p className="text-osce-caption text-b2b-mid">
          Publishing stays off until at least one station has been marked.
        </p>
      ) : null}

      <Button
        themeType="b2b"
        variant="secondary"
        isLoading={busy === "publish"}
        disabled={busy !== null || marked === 0}
        onClick={() => void publish()}
      >
        <HiCheckCircle className="h-4 w-4 shrink-0 text-b2b-success-text" aria-hidden />
        Publish circuit feedback
      </Button>
    </section>
  );
}
