"use client";

import Markdown from "react-markdown";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { StationBrief } from "@/capabilities/attempt-runner/material/StationBrief";
import { readSlotBrief, type MySlot, type SlotBrief } from "@/domains/assess/trainee/api";

/**
 * The reading brief for one slot, during the reading phase and after.
 *
 * One read, keyed on the slot: the circuit's attempt is created when the
 * patient is dispatched, after reading, and the station may be the org's own
 * or the platform library's. The server decides what a candidate may see
 * (`GET /me/slots/{id}/brief`); a templated station answers sections, an
 * older one a Markdown text.
 */
export function SlotReadingBrief({ slot }: { slot: MySlot }) {
  const state = useAsync((signal) => readSlotBrief(slot.id, signal), [slot.id]);

  return (
    <AsyncBoundary state={state}>
      {(brief: SlotBrief) =>
        brief.sections.length > 0 ? (
          <StationBrief brief={brief} />
        ) : brief.text ? (
          <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4 sm:p-5">
            <h3 className="text-osce-body font-semibold text-b2b-headline mb-3">Reading brief</h3>
            <div className="max-w-3xl text-sm leading-6 text-ink">
              <Markdown>{brief.text}</Markdown>
            </div>
          </div>
        ) : null
      }
    </AsyncBoundary>
  );
}
