"use client";

import Link from "next/link";
import { format } from "date-fns";
import { HiChevronRight, HiOutlineChatBubbleLeftRight } from "react-icons/hi2";
import { AsyncBoundary, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { debriefDate, listDebriefs } from "@/capabilities/debrief/api";

const { b2cCard, b2cGroupedRow, b2cGroupedRowSubtitle, b2cGroupedRowTitle } = productTokens;

/**
 * The debriefs someone has had.
 *
 * `attemptId` narrows it to one station's, which is how the retiring client
 * showed it — as a tab beside that station's feedback. Left out, it is the
 * whole history, because the backend keys debriefs on the attempt and not on
 * the station, so "this station's debriefs" is a filter rather than a call.
 */
export function DebriefHistory({ attemptId }: { attemptId?: string } = {}) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => {
      const debriefs = await listDebriefs(signal);
      return attemptId ? debriefs.filter((debrief) => debrief.attempt_id === attemptId) : debriefs;
    },
    [attemptId],
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
