"use client";

import { HiOutlineVideoCamera } from "react-icons/hi2";
import { Badge, Button } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import type { Slot } from "@/capabilities/peer-practice/api";
import { clockTime, isPast, shortDate } from "@/capabilities/peer-practice/support/time";
import { b2cCard } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";

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

  const posterDisplay = slot.is_mine ? "You" : atHandle(slot.owner_username, "Anonymous");
  const claimerDisplay =
    slot.claimed_by_user_id && currentUserId && slot.claimed_by_user_id === currentUserId
      ? "You"
      : atHandle(slot.claimed_by_username, "Partner");

  const scheduleLine = `${shortDate(slot.starts_at)}, ${clockTime(slot.starts_at)}`;
  const posterName = slot.is_mine ? "You" : slot.owner_username || "Anonymous";
  const description = completed
    ? slot.is_mine
      ? `You practised with ${claimerDisplay}`
      : slot.claimed_by_user_id && currentUserId && slot.claimed_by_user_id === currentUserId
        ? `You practised with ${posterDisplay}`
        : `${posterDisplay} practised with ${claimerDisplay}`
    : scheduled
      ? `Booked with ${slot.is_mine ? claimerDisplay : posterDisplay}`
      : slot.note?.trim() || "is looking for a practice partner";

  return (
    <section className={cn(b2cCard, "flex w-full min-w-0 flex-col p-5")}>
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-b2c-surface-muted text-osce-meta font-semibold text-osce-ink-700">
          {getInitial(posterName)}
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-osce-body font-medium text-osce-ink-900">
            {claimed ? `${posterDisplay} · ${claimerDisplay}` : posterDisplay}
          </p>
          <p className="line-clamp-2 text-osce-meta text-b2c-text-muted">{description}</p>
        </div>
        <Badge tone={available || completed ? "success" : scheduled ? "accent" : "neutral"} dot={available}>
          {available && slot.is_mine ? "Your post" : badgeLabel}
        </Badge>
      </div>

      <p className="mt-4 flex items-center gap-2 font-mono text-osce-meta tabular-nums text-osce-ink-700">
        <HiOutlineVideoCamera className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
        {scheduleLine}
      </p>

      {available && !slot.is_mine && !expired ? (
        <Button type="button" onClick={() => onClaim(slot)} isLoading={isClaiming} className="mt-4 w-full">
          Claim slot
        </Button>
      ) : null}

      {slot.is_mine && available && !expired && onWithdraw ? (
        <Button type="button" variant="secondary" onClick={() => onWithdraw(slot.id)} className="mt-4 w-full">
          Cancel post
        </Button>
      ) : null}
    </section>
  );
}
