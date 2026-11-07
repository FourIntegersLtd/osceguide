"use client";

import { useAsync } from "@/foundation/hooks";
import { assessMeta } from "@/foundation/ui/b2bTokens";
import type { Scheme } from "@/domains/assess/room/api";
import { PeerScheme } from "@/domains/assess/room/PeerScheme";

/**
 * Loads the scheme for the station running now and lets the watcher mark it as they go. A quiet line
 * while it loads, nothing it cannot show.
 */
export function LiveScheme({
  load,
  stationKey,
  circuitId,
}: {
  load: (signal: AbortSignal) => Promise<Scheme>;
  stationKey: string | null;
  circuitId: string;
}) {
  return stationKey ? (
    <Loaded load={load} stationKey={stationKey} circuitId={circuitId} />
  ) : (
    <p className={`${assessMeta} p-5`}>The scheme appears when a station is running.</p>
  );
}

function Loaded({ load, stationKey, circuitId }: { load: (signal: AbortSignal) => Promise<Scheme>; stationKey: string; circuitId: string }) {
  const state = useAsync(load, [stationKey]);
  if (state.loading) return <p className={`${assessMeta} p-5`}>Loading the scheme...</p>;
  if (!state.data) return <p className={`${assessMeta} p-5`}>The scheme is not available for this station.</p>;
  return <PeerScheme key={stationKey} scheme={state.data} circuitId={circuitId} slotId={stationKey} />;
}
