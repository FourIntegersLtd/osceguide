import React from "react";
import Link from "next/link";
import { cn } from "@/foundation/ui/cn";
import { b2cBodyText, b2cSectionTitle } from "@/foundation/ui/productTokens";

interface StationCompletionProgressBarProps {
  completedCount: number;
  subscriptionExpired: boolean;
  totalCount: number;
  /** undefined while the signed-in user is still resolving; never assume free. */
  hasPaid: boolean | undefined;
  freeLimit?: number;
  label?: string;
}

function StationCompletionProgressBar({
  completedCount = 0,
  totalCount = 0,
  hasPaid,
  subscriptionExpired = false,
  freeLimit = 3,
  label,
}: StationCompletionProgressBarProps) {
  // A user object that has not resolved yet (or that came back without the
  // field) must not be read as "free tier" - that flashes "3 of 3 free
  // stations" at a subscriber until the next refresh.
  const isPlanPending = typeof hasPaid !== "boolean";
  const isExpiredAndUnpaid = !isPlanPending && !hasPaid && subscriptionExpired;
  // The station catalogue loads after this renders, so totalCount is briefly 0.
  // Without this the bar would read "31 of 0 stations" and sit at 100%.
  const isTotalPending = isPlanPending || (hasPaid === true && totalCount <= 0);
  const denominator = hasPaid ? Math.max(totalCount, 1) : Math.max(freeLimit, 1);
  const percentage = isExpiredAndUnpaid
    ? 100
    : isTotalPending
      ? 0
      : Math.min((completedCount / denominator) * 100, 100);
  const freeUsedUp =
    !isPlanPending && !hasPaid && !isExpiredAndUnpaid && completedCount >= freeLimit;
  // station_progress is a lifetime total, so a user who practised before the free
  // tier existed can be well past the limit. Cap it so the label never reads "31 of 3".
  const freeUsedCount = Math.min(completedCount, freeLimit);

  const progressLabel =
    label ||
    (() => {
      if (isTotalPending) {
        return "";
      }
      if (hasPaid) {
        return `You have completed ${completedCount} of ${totalCount} stations`;
      }
      if (isExpiredAndUnpaid) {
        return `Your plan has ended. You completed ${completedCount} stations.`;
      }
      return `You have completed ${freeUsedCount} of ${freeLimit} free stations`;
    })();

  return (
    <div className="flex flex-col space-y-4">
      <h3 className={cn(b2cSectionTitle, "text-center")}>Your progress</h3>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(percentage)}
        aria-label={progressLabel || "Your progress"}
        className="h-2.5 w-full overflow-hidden rounded-full bg-b2c-secondary"
      >
        <div
          className="h-full rounded-full bg-osce-accent transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
      {progressLabel ? (
        <span className={cn(b2cBodyText, "flex justify-center text-center font-medium")}>
          {progressLabel}
        </span>
      ) : null}
      {isExpiredAndUnpaid || freeUsedUp ? (
        <p className="text-center text-osce-meta text-b2c-text-muted">
          {isExpiredAndUnpaid
            ? "Renew to unlock every station again."
            : "You've used your free stations. Upgrade to keep practising."}{" "}
          <Link href="/settings?tab=payments" className="font-semibold text-osce-accent hover:underline">
            See plans
          </Link>
        </p>
      ) : null}
    </div>
  );
}

export default StationCompletionProgressBar;
