"use client";

import { HiOutlineVideoCamera } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { b2cCard, b2cGhostButton } from "@/foundation/ui/productTokens";
import { useSession } from "@/foundation/session";
import type { Slot } from "@/capabilities/peer-practice/api";
import { clockTime, isPast, shortDate } from "@/capabilities/peer-practice/support/time";

function getInitial(name: string) {
  return (name || "?").charAt(0).toUpperCase();
}

function atHandle(username: string | null | undefined, fallback: string) {
  const raw = (username || fallback).replace(/^@/, "");
  return `@${raw}`;
}

/**
 * One offered slot — same four display states and copy as B2C `AvailabilityPostCard`.
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
  const { session } = useSession();
  const currentUserId = session?.user.id ?? null;

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

  const posterDisplay = slot.is_mine ? "You" : atHandle(slot.owner_username, "Anonymous");
  const claimerDisplay =
    slot.claimed_by_user_id && currentUserId && slot.claimed_by_user_id === currentUserId
      ? "You"
      : atHandle(slot.claimed_by_username, "Partner");

  const scheduleLine = `${shortDate(slot.starts_at)}, ${clockTime(slot.starts_at)}`;

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
                {getInitial(slot.is_mine ? "You" : slot.owner_username || "Anonymous")}
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-white bg-b2c-secondary font-medium text-b2c-text-secondary">
                {claimed ? getInitial(slot.claimed_by_username || "P") : "?"}
              </div>
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-osce-ink-900">
                {claimed ? `${posterDisplay} · ${claimerDisplay}` : posterDisplay}
              </p>
              <p className="text-b2c-text-muted">
                {completed
                  ? " Session completed"
                  : scheduled
                    ? "Session booked"
                    : "Video practice"}
              </p>
            </div>
          </div>

          <div className="rounded-lg bg-b2c-surface-muted p-3 text-b2c-text-secondary">
            {completed ? (
              <>
                <p className="mt-0.5">
                  {slot.is_mine
                    ? `You practiced with ${claimerDisplay}`
                    : slot.claimed_by_user_id && currentUserId && slot.claimed_by_user_id === currentUserId
                      ? `You practiced with ${posterDisplay}`
                      : `${posterDisplay} practiced with ${claimerDisplay}`}
                </p>
                <p className="font-medium text-b2c-text-secondary">
                  {slot.note?.trim() ? slot.note : "Video practice session finished"}
                </p>
              </>
            ) : (
              <>
                <p className="mt-0.5">
                  {slot.note && available
                    ? slot.note
                    : scheduled
                      ? "Session scheduled:"
                      : slot.is_mine
                        ? "I am looking for a practice partner."
                        : `${atHandle(slot.owner_username, "User")} is looking for a practice partner.`}
                </p>
                <p className="font-medium text-b2c-text-secondary">{scheduleLine}</p>
              </>
            )}
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
