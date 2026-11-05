"use client";

import { usePathname } from "next/navigation";
import { useAsync, useEventStream } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import type { Surface } from "@/capabilities";
import { liveBoardStreamPath, readLiveBoard, type LiveBoard } from "@/domains/assess/dashboard/api";
import { attentionFromResults } from "@/domains/assess/dashboard/support";
import { readResultsIndex } from "@/domains/assess/results/api";
import { INSTITUTION_WORDS } from "@/domains/assess/vocabulary";
import { navBadgeGate, navBadges, type NavBadges } from "@/surfaces/navBadges";

/**
 * The count chips of an organisation's menu: "Now running 1 live" and, for someone who signs
 * results off, "Results 5".
 *
 * Two reads and one stream, never polled: the live board (initial read, then its stream) and the
 * results index (one request). The index is read again when the running count changes, which is
 * what a circuit ending does, and when the screen changes. A supervisor who signs nothing off sees
 * no Results chip: their count would take a console read per circuit. A failed read shows no chip.
 */
export function useNavBadges(surface: Surface, orgSlug: string | null): NavBadges {
  const { session } = useSession();
  const pathname = usePathname();
  const gate = navBadgeGate(surface, can(session, "run_circuits"), can(session, "sign_off_results"));
  const org = gate.live ? orgSlug : null;

  const initial = useAsync((signal) => (org ? readLiveBoard(org, signal) : Promise.resolve(null)), [org]);
  const stream = useEventStream<LiveBoard>(org ? liveBoardStreamPath(org) : null, { enabled: org !== null });
  const running = (stream.data ?? initial.data)?.circuits?.length ?? 0;

  const decides = org !== null && gate.results;
  const index = useAsync(
    (signal) => (decides && org ? readResultsIndex(org, signal) : Promise.resolve(null)),
    [org, decides, running, pathname],
  );
  const attention = index.data ? attentionFromResults(index.data.rows ?? [], INSTITUTION_WORDS).length : null;

  if (!org) return { live: undefined, results: undefined };
  return navBadges(running, attention);
}
