"use client";

import { useState } from "react";
import { Alert, EmptyState, Spinner } from "@/foundation/ui";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import { boardCard, boardRow } from "@/foundation/ui/boardKit";
import { useAsync } from "@/foundation/hooks";
import { listInterventions } from "@/domains/assess/sessions/api";

/** The override actions, as an examiner would write them in a report. */
const ACTION_LABEL: Record<string, string> = {
  advance: "Advanced to the next station",
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
    <section className={boardCard}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left text-assess-label font-medium text-osce-ink-900 hover:bg-osce-canvas"
      >
        <span>What was changed by hand</span>
        <span className={assessMeta}>{open ? "Hide" : "Show"}</span>
      </button>
      {open ? (
        <div className="border-t border-osce-border-light px-5 pb-1">
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
    return <Alert tone="danger">Could not load the log. {log.error.message}</Alert>;
  }

  const items = log.data?.items ?? [];
  if (items.length === 0) {
    return <EmptyState title="Nobody has stepped in on this circuit." />;
  }

  return (
    <ol className="m-0 list-none p-0">
      {items.map((entry) => (
        <li key={entry.id} className={`${boardRow} px-0`}>
          <span className="min-w-0 flex-[1_1_240px]">
            {ACTION_LABEL[entry.action] ?? entry.action.replace(/_/g, " ")}
            <span className={`block ${assessMeta}`}>
              {`${new Date(entry.at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })} · ${entry.reason ?? "No reason was given."}`}
            </span>
          </span>
        </li>
      ))}
    </ol>
  );
}
