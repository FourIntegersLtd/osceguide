"use client";

import Link from "next/link";
import { format } from "date-fns";
import { HiChevronRight, HiOutlineChatBubbleLeftRight } from "react-icons/hi2";
import { AsyncBoundary, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";
import { debriefDate, listDebriefs } from "@/capabilities/debrief/api";

const { b2cCard, b2cGroupedRow, b2cGroupedRowSubtitle, b2cGroupedRowTitle } = productTokens;

/**
 * The debriefs someone has had.
 *
 * Station/set scope includes every source consultation, not just the latest
 * attempt. Without that scope, attemptId narrows to one consultation; with
 * neither it shows the learner's complete history.
 */
export function DebriefHistory({ attemptId, stationVersionId, entryId }: {
  attemptId?: string;
  stationVersionId?: string | null;
  entryId?: string | null;
} = {}) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => {
      const debriefs = await listDebriefs(signal);
      if (stationVersionId || entryId) {
        const sources = new Set<string>();
        let cursor: string | null | undefined;
        do {
          const page = await listMyAttempts({ stationVersionId, setEntryId: entryId, limit: 100, cursor }, signal);
          page.items.forEach((item) => sources.add(item.id));
          cursor = page.next_cursor;
        } while (cursor && !signal.aborted);
        return debriefs.filter((debrief) => debrief.source_attempt_id && sources.has(debrief.source_attempt_id));
      }
      return attemptId ? debriefs.filter((debrief) => debrief.source_attempt_id === attemptId) : debriefs;
    },
    [attemptId, stationVersionId, entryId],
  );

  return (
    <AsyncBoundary
      state={state}
      empty={{
        title: "No Debrief History Found",
        description:
          "You haven’t had any debrief sessions yet. Start a debrief from a station you have already sat to talk your consultation through with Athena.",
      }}
    >
      {(debriefs) => (
        <div className={`${b2cCard} overflow-hidden`}>
          {debriefs.map((debrief) => {
            const created = debriefDate(debrief.created_at);
            return (
              <Link
                href={hrefFor(`/debriefs/${debrief.id}`)}
                key={debrief.id}
                className={b2cGroupedRow}
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-osce-accent-subtle">
                  <HiOutlineChatBubbleLeftRight className="h-5 w-5 text-osce-accent" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className={b2cGroupedRowTitle}>Debrief Session</p>
                  <p className={b2cGroupedRowSubtitle}>
                    {created ? format(created, "PPP p") : ""}
                  </p>
                </div>
                <HiChevronRight className="h-5 w-5 shrink-0 text-b2c-text-muted" />
              </Link>
            );
          })}
        </div>
      )}
    </AsyncBoundary>
  );
}
