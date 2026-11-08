"use client";

import { JoinRoom } from "@/domains/assess/trainee/JoinRoom";
import { SlotReadingBrief } from "@/domains/assess/trainee/SlotReadingBrief";
import { activeSlot } from "@/domains/assess/trainee/support";
import type { MySitting } from "@/domains/assess/trainee/api";
import { LiveScheme } from "@/domains/assess/room/SchemeView";
import { SidePanel } from "@/domains/assess/room/SidePanel";
import { SplitCard } from "@/domains/assess/room/SplitCard";
import { readSchemeForTrainee } from "@/domains/assess/room/api";

/**
 * A practice circuit's room for a trainee: one card, the group video call on the left and beside it the
 * one thing they need now. Their own turn shows their brief; anyone else's shows the marking scheme of
 * the station running, which they mark as they watch.
 */
export function TrainingRoom({ sitting }: { sitting: MySitting }) {
  const mine = activeSlot(sitting);
  const running = sitting.active_slot_id ?? null;
  const title = mine ? "Your brief" : "Marking scheme";

  return (
    <SplitCard
      sideTitle={title}
      main={<JoinRoom sitting={sitting} />}
      side={
        mine ? (
          <SidePanel title={title}>
            <SlotReadingBrief slot={mine} embedded fold />
          </SidePanel>
        ) : running ? (
          <LiveScheme stationKey={running} load={(signal) => readSchemeForTrainee(sitting.circuit_id, signal)} circuitId={sitting.circuit_id} />
        ) : (
          <SidePanel title={title}>
            <p className="p-4 text-assess-meta text-osce-ink-500">The scheme appears when a station is running.</p>
          </SidePanel>
        )
      }
    />
  );
}
