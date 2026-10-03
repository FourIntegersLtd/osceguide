import React from "react";
import Link from "next/link";
import { B2CHero } from "@/foundation/ui/B2CHero";

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

  const remaining = hasPaid && !isTotalPending ? Math.max(totalCount - completedCount, 0) : null;
  const shown = hasPaid ? completedCount : freeUsedCount;
  const outOf = hasPaid ? totalCount : freeLimit;

  // Canvas `train-practice`: a grey panel, the count as its heading, the bar on the right.
  return (
    <B2CHero
      eyebrow="Your progress"
      title={progressLabel || "Your progress"}
      aside={
        <div className="w-full shrink-0 sm:w-[220px]">
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(percentage)}
            aria-label={progressLabel || "Your progress"}
            className="h-2 w-full overflow-hidden rounded-full bg-osce-navActive"
          >
            <div
              className="h-full rounded-full bg-osce-accent transition-all duration-500"
              style={{ width: `${percentage}%` }}
            />
          </div>
          {!isTotalPending ? (
            <p className="mt-2 text-right text-osce-meta tabular-nums text-b2c-text-muted">
              {shown} / {outOf}
            </p>
          ) : null}
        </div>
      }
    >
      {isExpiredAndUnpaid || freeUsedUp ? (
        <>
          {isExpiredAndUnpaid
            ? "Renew to unlock every station again."
            : "You've used your free stations. Upgrade to keep practising."}{" "}
          <Link href="/settings?tab=payments" className="font-medium text-osce-accent hover:text-osce-accent-hover">
            See plans
          </Link>
        </>
      ) : remaining !== null ? (
        `${remaining} ${remaining === 1 ? "station" : "stations"} left. A session of 3 stations takes about 45 minutes.`
      ) : null}
    </B2CHero>
  );
}

export default StationCompletionProgressBar;
