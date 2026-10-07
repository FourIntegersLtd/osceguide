"use client";

import { HiMicrophone } from "react-icons/hi";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import { AsyncBoundary, Button } from "@/foundation/ui";
import type { AsyncState } from "@/foundation/hooks";

/**
 * The debrief buttons, shown once the attempt has a marking.
 *
 * Whether it is marked is a read that can fail. A failure says so with a retry; before, it
 * looked the same as "not marked yet" and the buttons simply never appeared.
 */
export function DebriefActions({
  markedState,
  loadingDebrief,
  onExplain,
  onStart,
}: {
  markedState: AsyncState<unknown[]>;
  loadingDebrief: boolean;
  onExplain: () => void;
  onStart: () => void;
}) {
  return (
    <AsyncBoundary state={markedState} loading={null} isEmpty={() => false}>
      {(results) =>
        results.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2 sm:justify-end">
            <Button type="button" variant="ghost" onClick={onExplain} className="gap-2">
              <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
              How debrief works
            </Button>
            <Button type="button" onClick={onStart} isLoading={loadingDebrief} className="gap-2">
              <HiMicrophone className="h-4 w-4" aria-hidden />
              Start debrief
            </Button>
          </div>
        ) : null
      }
    </AsyncBoundary>
  );
}
