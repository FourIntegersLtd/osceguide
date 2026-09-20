"use client";

import { HiOutlineCalendarDays } from "react-icons/hi2";
import { B2CEmptyState } from "@/foundation/ui";
import type { Slot } from "@/capabilities/peer-practice/api";
import { SlotCard } from "@/capabilities/peer-practice/marketplace/SlotCard";
import { isPast, startMs } from "@/capabilities/peer-practice/support/time";

export interface SlotActions {
  onClaim: (slot: Slot) => void;
  onWithdraw: (postId: string) => void;
  claimingId: string | null;
}

function byMostRecent(a: Slot, b: Slot): number {
  return startMs(b.starts_at) - startMs(a.starts_at);
}

function SlotGrid({ slots, actions }: { slots: Slot[]; actions: SlotActions }) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:gap-4 md:grid-cols-2">
      {slots.map((slot) => (
        <SlotCard
          key={slot.id}
          slot={slot}
          onClaim={actions.onClaim}
          onWithdraw={actions.onWithdraw}
          isClaiming={actions.claimingId === slot.id}
        />
      ))}
    </div>
  );
}

function SectionHeading({ children }: { children: string }) {
  return (
    <h3 className="mb-3 text-osce-body font-semibold text-osce-ink-900">{children}</h3>
  );
}

/**
 * Every slot, grouped the way the retiring screen grouped them.
 *
 * Available, then Scheduled, then Completed — most recent first inside each.
 * The client loads the full feed (available + claimed) for the current exam,
 * then splits it here the way the retiring B2C screen did.
 */
export function SlotSections({ slots, actions }: { slots: Slot[]; actions: SlotActions }) {
  const claimed = slots.filter((slot) => slot.status === "claimed");
  const available = slots.filter((slot) => slot.status === "available" && !isPast(slot.starts_at));
  const scheduled = claimed.filter((slot) => !isPast(slot.starts_at)).sort(byMostRecent);
  const completed = claimed.filter((slot) => isPast(slot.starts_at)).sort(byMostRecent);
  const sorted = [...available].sort(byMostRecent);

  if (sorted.length === 0 && scheduled.length === 0 && completed.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlineCalendarDays}
        title="No open slots right now"
        description="Be the first to post your availability!"
      />
    );
  }

  return (
    <div className="space-y-8">
      {sorted.length > 0 && (
        <section>
          <SectionHeading>Available</SectionHeading>
          <SlotGrid slots={sorted} actions={actions} />
        </section>
      )}
      {scheduled.length > 0 && (
        <section>
          <SectionHeading>Scheduled</SectionHeading>
          <SlotGrid slots={scheduled} actions={actions} />
        </section>
      )}
      {completed.length > 0 && (
        <section>
          <SectionHeading>Completed</SectionHeading>
          <SlotGrid slots={completed} actions={actions} />
        </section>
      )}
    </div>
  );
}

/** The "My Sessions" tab: the slots this person offered, and nothing else. */
export function MySlots({ slots, actions }: { slots: Slot[]; actions: SlotActions }) {
  const mine = slots.filter((slot) => slot.is_mine).sort(byMostRecent);
  if (mine.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlineCalendarDays}
        title="You haven't posted any availability yet"
        description="Post your availability to find a practice partner!"
      />
    );
  }
  return <SlotGrid slots={mine} actions={actions} />;
}
