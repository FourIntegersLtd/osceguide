"use client";

import { useState } from "react";
import { Alert, EmptyState, Spinner, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import { listInterventions } from "@/domains/assess/sessions/api";

/** The override actions, as an examiner would write them in a report. */
const ACTION_LABEL: Record<string, string> = {
  pause: "Paused",
  resume: "Resumed",
  extend_clock: "Clock extended",
  reset_clock: "Clock reset",
  resend_patient: "Patient resent",
  redo_station: "Station redone",
  jump_to: "Jumped to a station",
  auto_advance: "Auto-advance changed",
};

/**
 * Everything a human did to this examination, and why.
 *
 * This is the half of the overrides that makes them defensible: an examination
 * that was paused for eleven minutes needs to be able to say it was the fire
 * alarm. The retiring runner recorded none of it — the clock lived in a
 * browser, so there was nothing to record it against.
 *
 * Loaded when it is opened. An examination in progress is not the moment to
 * spend a request on a log nobody has asked for.
 */
export function InterventionsLog({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  const [open, setOpen] = useState(false);

  return (
    <section className="overflow-hidden rounded-lg border border-b2b-border bg-white">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-b2b-cream/60 sm:px-5"
      >
        <span className={b2bTokens.b2bSectionTitle}>What was changed by hand</span>
        <span className="text-osce-caption text-b2b-mid">{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="border-t border-b2b-border p-4 sm:p-5">
          <Entries orgSlug={orgSlug} circuitId={circuitId} />
        </div>
      ) : null}
    </section>
  );
}

function Entries({ orgSlug, circuitId }: { orgSlug: string; circuitId: string }) {
  const log = useAsync(
    (signal) => listInterventions(orgSlug, circuitId, signal),
    [orgSlug, circuitId],
  );

  if (log.loading) return <Spinner />;
  if (log.error) {
    return <Alert tone="danger">That record could not be read. {log.error.message}</Alert>;
  }

  const items = log.data?.items ?? [];
  if (items.length === 0) {
    return <EmptyState title="Nothing on this circuit has been overridden." />;
  }

  return (
    <ol className="divide-y divide-b2b-border">
      {items.map((entry) => (
        <li key={entry.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
          <div className="min-w-0">
            <p className="text-osce-caption font-semibold text-b2b-headline">
              {ACTION_LABEL[entry.action] ?? entry.action.replace(/_/g, " ")}
            </p>
            <p className="text-osce-caption text-b2b-mid">
              {entry.reason ?? "No reason was given."}
            </p>
          </div>
          <span className="shrink-0 text-osce-caption text-b2b-icon">{formatWhen(entry.at)}</span>
        </li>
      ))}
    </ol>
  );
}
