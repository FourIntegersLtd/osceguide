"use client";

import { HiOutlineCalendarDays } from "react-icons/hi2";
import { Alert, B2CEmptyState, Button } from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
import { listSlots, MARKETPLACE_PAGE_SIZE, type Slot } from "@/capabilities/peer-practice/api";
import { SlotCard } from "@/capabilities/peer-practice/marketplace/SlotCard";
import { startMs } from "@/capabilities/peer-practice/support/time";

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

type SectionFilter = { status: "available" | "claimed"; when: "upcoming" | "past" };

const SECTIONS: { heading: string; filter: SectionFilter }[] = [
  { heading: "Available", filter: { status: "available", when: "upcoming" } },
  { heading: "Scheduled", filter: { status: "claimed", when: "upcoming" } },
  { heading: "Completed", filter: { status: "claimed", when: "past" } },
];

/** One section of the marketplace: the server filters, orders and pages it. */
function SlotSection({
  heading,
  filter,
  orgId,
  examCode,
  reloadKey,
  actions,
}: {
  heading: string;
  filter: SectionFilter;
  orgId: string | null;
  examCode: string | null;
  reloadKey: number;
  actions: SlotActions;
}) {
  const pages = useCursorPages(
    (cursor, signal) =>
      listSlots({ cursor, orgId, examCode, limit: MARKETPLACE_PAGE_SIZE, ...filter }, signal),
    [orgId, examCode, reloadKey, filter.status, filter.when],
  );
  const slots = pages.state.data ?? [];
  if (pages.state.error) {
    return <Alert tone="danger">Could not load {heading.toLowerCase()} sessions: {pages.state.error.message}</Alert>;
  }
  if (slots.length === 0) return null;
  return (
    <section>
      <SectionHeading>{heading}</SectionHeading>
      <SlotGrid slots={slots} actions={actions} />
      {pages.moreError ? (
        <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
      ) : null}
      {pages.hasMore ? (
        <div className="mt-3 flex justify-center">
          <Button variant="secondary" size="sm" disabled={pages.loadingMore} onClick={pages.loadMore}>
            {pages.loadingMore ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

/**
 * The marketplace: Available, then Scheduled, then Completed.
 *
 * Each section is its own server query (status + when), ordered most recent
 * first by the server, so nothing is filtered or sorted in the browser.
 */
export function SlotSections({
  orgId,
  examCode,
  reloadKey,
  actions,
}: {
  orgId: string | null;
  examCode: string | null;
  reloadKey: number;
  actions: SlotActions;
}) {
  return (
    <div className="space-y-8">
      {SECTIONS.map((section) => (
        <SlotSection
          key={section.heading}
          heading={section.heading}
          filter={section.filter}
          orgId={orgId}
          examCode={examCode}
          reloadKey={reloadKey}
          actions={actions}
        />
      ))}
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
