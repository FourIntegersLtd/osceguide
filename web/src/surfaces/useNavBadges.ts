"use client";

import { useAsync, useEventStream } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import type { Surface } from "@/capabilities";
import { liveBoardStreamPath, readLiveBoard, type LiveBoard } from "@/domains/assess/dashboard/api";
import { attentionFromResults } from "@/domains/assess/dashboard/support";
import { readResultsIndex } from "@/domains/assess/results/api";
import { useStationsToReview } from "@/domains/assess/results/StationsToReview";
import { INSTITUTION_WORDS } from "@/domains/assess/vocabulary";

/**
 * The count chips of an organisation's menu: "Now running 1 live" and "Results 5".
 *
 * From reads the home screen already makes: the live board's stream (never polled) and the
 * results index, or for a supervisor who signs nothing off, their stations still to review.
 * A failed read shows no chip rather than a wrong one.
 */
export function useNavBadges(surface: Surface, orgSlug: string | null): { live?: string; results?: string } {
  const { session } = useSession();
  const org = (surface === "assess" || surface === "hire") && orgSlug && can(session, "run_circuits") ? orgSlug : null;
  const decides = can(session, "sign_off_results");

  const initial = useAsync((signal) => (org ? readLiveBoard(org, signal) : Promise.resolve(null)), [org]);
  const stream = useEventStream<LiveBoard>(org ? liveBoardStreamPath(org) : null, { enabled: org !== null });
  const running = (stream.data ?? initial.data)?.circuits?.length ?? 0;

  const index = useAsync(
    (signal) => (org && decides ? readResultsIndex(org, signal) : Promise.resolve(null)),
    [org, decides],
  );
  const { stations } = useStationsToReview(org && !decides ? org : null);
  const results = decides ? attentionFromResults(index.data?.rows ?? [], INSTITUTION_WORDS).length : stations.length;

  if (!org) return {};
  return {
    live: running > 0 ? `${running} live` : undefined,
    results: results > 0 ? String(results) : undefined,
  };
}
