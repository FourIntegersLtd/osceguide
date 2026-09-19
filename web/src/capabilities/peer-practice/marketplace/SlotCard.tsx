"use client";

import { HiOutlineVideoCamera } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { b2cCard, b2cGhostButton } from "@/foundation/ui/productTokens";
import type { Slot } from "@/capabilities/peer-practice/api";
import { clockTime, isPast, shortDate } from "@/capabilities/peer-practice/support/time";

/**
 * One offered slot.
 *
 * The four display states are the retiring card's, unchanged — Available,
 * Scheduled, Completed, Expired — because they are what a reader recognises.
 * What changed underneath is where they come from: a status and one instant,
 * rather than a status plus a calendar date plus a wall-clock time that three
 * components each re-assembled their own way.
 */
export function SlotCard({
  slot,
  onClaim,
  onWithdraw,
  isClaiming = false,
}: {
  slot: Slot;
  onClaim: (slot: Slot) => void;
  onWithdraw?: (postId: string) => void;
  isClaiming?: boolean;
}) {
  const past = isPast(slot.starts_at);
  const claimed = slot.status === "claimed";
  const available = slot.status === "available" && !past;
  const scheduled = claimed && !past;
  const completed = claimed && past;
  const expired = (slot.status === "available" || slot.status === "expired") && past;

  const badgeLabel = available
    ? "Available"
    : scheduled
      ? "Scheduled"
      : completed
        ? "Completed"
        : "Expired";
  const headerLabel = available
    ? "Open slot"
    : scheduled
      ? "Upcoming"
      : completed
        ? "Past session"
        : "No longer available";

  // `platform-api` answers with ids, not display names — see docs/port-gaps.md.
  const posterDisplay = slot.is_mine ? "You" : "A colleague";

  return (
    <div className="w-full min-w-0">
      <div className={`${b2cCard} overflow-hidden`}>
        <div className="flex items-center justify-between border-b border-b2c-border bg-b2c-surface-muted px-4 py-3">
          <span className="flex items-center gap-2 text-osce-body font-medium text-b2c-text-secondary">
            {available && (
              <HiOutlineVideoCamera className="h-4 w-4 flex-shrink-0 text-osce-success-text" />
            )}
            {scheduled && (
              <HiOutlineVideoCamera className="h-4 w-4 flex-shrink-0 text-osce-accent" />
            )}
            {completed && (
              <HiOutlineVideoCamera className="h-4 w-4 flex-shrink-0 text-b2c-text-muted" />
            )}
            {headerLabel}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-osce-caption font-semibold ${
              available
                ? "bg-osce-success-bg text-osce-success-text"
                : scheduled
                  ? "bg-osce-accent-subtle text-osce-accent-hover"
                  : completed
                    ? "bg-osce-success-bg text-osce-success-text"
                    : "bg-b2c-secondary text-b2c-text-secondary"
            }`}
          >
            {badgeLabel}
          </span>
        </div>

        <div className="space-y-4 p-3 sm:p-4">
          <div className="flex items-center gap-3">
            <div className="flex -space-x-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-osce-accent-subtle font-medium text-osce-accent">
                {slot.is_mine ? "Y" : "C"}
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-b2c-secondary font-medium text-b2c-text-secondary">
                ?
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-osce-ink-900">{posterDisplay}</p>
              <p className="text-b2c-text-muted">
                {completed
                  ? "Session completed"
                  : scheduled
                    ? "Session booked"
                    : "Video practice"}
              </p>
            </div>
          </div>

          <div className="rounded-lg bg-b2c-surface-muted p-3 text-b2c-text-secondary">
            <p className="mt-0.5">
              {slot.note && available
                ? slot.note
                : scheduled
                  ? "Session scheduled:"
                  : slot.is_mine
                    ? "I am looking for a practice partner."
                    : "A colleague is looking for a practice partner."}
            </p>
            <p className="font-medium text-b2c-text-secondary">
              {shortDate(slot.starts_at)}, {clockTime(slot.starts_at)} ·{" "}
              {slot.duration_minutes} minutes · {slot.exam_code.toUpperCase()}
            </p>
          </div>

          {available && !slot.is_mine && !expired && (
            <div className="flex sm:justify-end">
              <Button
                type="button"
                variant="primary"
                size="md"
                onClick={() => onClaim(slot)}
                disabled={isClaiming}
                className="w-full sm:w-auto"
              >
                {isClaiming ? "Claiming..." : "Claim slot"}
              </Button>
            </div>
          )}

          {slot.is_mine && available && !expired && onWithdraw && (
            <button
              type="button"
              onClick={() => onWithdraw(slot.id)}
              className={`w-full ${b2cGhostButton}`}
            >
              Cancel post
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
