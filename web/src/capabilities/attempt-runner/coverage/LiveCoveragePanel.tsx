"use client";

import { useCallback, useSyncExternalStore } from "react";
import { HiOutlineClipboardDocumentCheck, HiOutlineEye, HiOutlineXMark } from "react-icons/hi2";
import { B2CPanelCardHeader, B2CPanelCardHeaderIcon } from "@/foundation/ui";
import { useAsync, useMeEvents } from "@/foundation/hooks";
import { readCoverage, type CoverageUpdate } from "./api";
import LiveCoverageFeed from "./LiveCoverageFeed";
import { getLiveCoverageHidden, getLiveCoverageHiddenOnServer, setLiveCoverageHidden, subscribeLiveCoverageHidden } from "./preference";

const EMPTY: CoverageUpdate = { supported: false, items: [], last_seq: -1 };

/**
 * The "What you've covered" column of the consultation card. Open by default,
 * with a close button in its header; closed, the column keeps only the line
 * that reopens it, because nobody discovers a panel that starts switched off.
 */
export function LiveCoveragePanel({ attemptId, isLive, patientJoined = true }: {
  attemptId: string | null;
  isLive: boolean;
  /** The rubric is frozen when the patient's worker starts, so coverage is read again when it joins. */
  patientJoined?: boolean;
}) {
  const hidden = useSyncExternalStore(subscribeLiveCoverageHidden, getLiveCoverageHidden, getLiveCoverageHiddenOnServer);
  const state = useAsync((signal) => attemptId && !hidden
    ? readCoverage(attemptId, signal) : Promise.resolve(EMPTY), [attemptId, hidden, patientJoined]);
  const reload = state.reload;
  // `update_coverage` publishes `coverage` to the attempt's owner as each item is
  // marked live, so this re-reads on that event rather than on a fixed interval.
  useMeEvents(
    attemptId && !hidden && isLive ? ["coverage"] : null,
    useCallback(
      (event) => {
        if (event.name === "resync" || event.data.attempt_id === attemptId) reload();
      },
      [attemptId, reload],
    ),
  );

  if (hidden) return <div className="px-4 py-3">
    <button type="button" onClick={() => setLiveCoverageHidden(false)}
      className="flex items-center gap-1.5 rounded-osce-sm text-osce-meta text-b2c-text-muted hover:text-osce-ink-900 focus:ring-2 focus:ring-osce-accent">
      <HiOutlineEye className="h-4 w-4" aria-hidden />Show live marking
    </button>
  </div>;

  return <div className="flex min-h-[240px] flex-1 flex-col overflow-hidden lg:min-h-0">
    <B2CPanelCardHeader className="justify-between">
      <span className="flex min-w-0 items-center gap-2.5">
        <B2CPanelCardHeaderIcon icon={HiOutlineClipboardDocumentCheck} tone="emerald" />
        What you&apos;ve covered
      </span>
      <button
        type="button"
        onClick={() => setLiveCoverageHidden(true)}
        aria-label="Hide live marking"
        className="shrink-0 rounded-osce-sm p-1 text-b2c-text-muted transition-colors hover:text-osce-ink-900 focus:outline-none focus:ring-2 focus:ring-osce-accent"
      >
        <HiOutlineXMark className="h-4 w-4" aria-hidden />
      </button>
    </B2CPanelCardHeader>
    <div className="flex min-h-0 flex-1 flex-col px-4 py-3">
      <LiveCoverageFeed coverage={state.data ?? null} isLive={isLive} maxVisible={12} supportKnown={patientJoined} />
      {state.error && <p role="status" className="mt-1 text-osce-meta text-b2c-text-muted">Live marking is reconnecting. Your consultation can continue.</p>}
    </div>
  </div>;
}
