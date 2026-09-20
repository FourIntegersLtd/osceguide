"use client";

import { useEffect, useSyncExternalStore } from "react";
import { HiOutlineEye } from "react-icons/hi2";
import { useAsync } from "@/foundation/hooks";
import { readCoverage, type CoverageUpdate } from "./api";
import LiveCoverageFeed from "./LiveCoverageFeed";
import { getLiveCoverageHidden, getLiveCoverageHiddenOnServer, setLiveCoverageHidden, subscribeLiveCoverageHidden } from "./preference";

const EMPTY: CoverageUpdate = { supported: false, items: [], last_seq: -1 };

export function LiveCoveragePanel({ attemptId, isLive }: { attemptId: string | null; isLive: boolean }) {
  const hidden = useSyncExternalStore(subscribeLiveCoverageHidden, getLiveCoverageHidden, getLiveCoverageHiddenOnServer);
  const state = useAsync((signal) => attemptId && !hidden
    ? readCoverage(attemptId, signal) : Promise.resolve(EMPTY), [attemptId, hidden]);
  const reload = state.reload;
  useEffect(() => {
    if (!attemptId || hidden || !isLive) return;
    const timer = window.setInterval(reload, 4000);
    return () => window.clearInterval(timer);
  }, [attemptId, hidden, isLive, reload]);

  if (hidden) return <div className="shrink-0 border-t border-b2c-border px-4 py-2.5">
    <button type="button" onClick={() => setLiveCoverageHidden(false)}
      className="flex items-center gap-1.5 rounded-osce-sm text-osce-meta text-b2c-text-muted hover:text-osce-ink-900 focus:ring-2 focus:ring-osce-accent">
      <HiOutlineEye className="h-4 w-4" aria-hidden />Show live marking
    </button>
  </div>;

  return <div className={`shrink-0 border-t border-b2c-border px-4 py-3 ${isLive || state.data?.items?.length ? "flex h-[45%] min-h-[172px] flex-col overflow-hidden" : ""}`}>
    <LiveCoverageFeed coverage={state.data ?? null} isLive={isLive} onHide={() => setLiveCoverageHidden(true)} maxVisible={8} />
    {state.error && <p role="status" className="mt-1 text-osce-meta text-b2c-text-muted">Live marking is reconnecting. Your consultation can continue.</p>}
  </div>;
}
