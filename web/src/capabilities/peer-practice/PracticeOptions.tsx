"use client";

import {
  HiOutlineArrowPath,
  HiOutlineArrowRight,
  HiOutlineCalendarDays,
  HiOutlineUsers,
} from "react-icons/hi2";

/**
 * The two ways to practise with a colleague, as a pair of cards.
 *
 * The retiring client's `PracticeOptions`, which the end of a session showed
 * under "Keep practising": join the live queue now, or go and find a time.
 * Presentational only; the screen that mounts it owns the queue it drives.
 */
export function PracticeOptionCards({
  onLivePractice,
  onSchedulePractice,
  isJoiningQueue = false,
  variant = "inline",
  livePracticeLabel = "Live practice",
  schedulePracticeLabel = "Schedule practice",
  livePracticeActionLabel = "Start now",
  schedulePracticeActionLabel = "Post availability",
}: {
  onLivePractice: () => void;
  onSchedulePractice: () => void;
  isJoiningQueue?: boolean;
  variant?: "modal" | "inline";
  livePracticeLabel?: string;
  schedulePracticeLabel?: string;
  livePracticeActionLabel?: string;
  schedulePracticeActionLabel?: string;
}) {
  const content = (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <button
        type="button"
        onClick={onLivePractice}
        disabled={isJoiningQueue}
        className="group cursor-pointer rounded-osce-lg border border-b2c-border bg-osce-surface p-4 transition-colors hover:bg-b2c-surface-muted disabled:cursor-not-allowed disabled:opacity-50"
      >
        <div className="flex flex-col items-center space-y-2.5 text-center">
          <div className="rounded-lg border border-b2c-border bg-b2c-surface-muted p-2.5">
            <HiOutlineUsers className="h-4 w-4 text-b2c-text-secondary" />
          </div>
          <div>
            <h3 className="mb-0.5 text-osce-body font-semibold text-osce-ink-900">
              {livePracticeLabel}
            </h3>
            <p className="text-osce-meta text-b2c-text-muted">Get matched immediately</p>
          </div>
          {isJoiningQueue ? (
            <div className="flex items-center gap-2 text-osce-accent">
              <HiOutlineArrowPath className="h-3.5 w-3.5 animate-spin" />
              <span className="text-osce-body font-medium">Joining…</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-osce-accent transition-all duration-200 group-hover:gap-2.5">
              <span className="text-osce-body font-medium">{livePracticeActionLabel}</span>
              <HiOutlineArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </div>
          )}
        </div>
      </button>

      <button
        type="button"
        onClick={onSchedulePractice}
        className="group cursor-pointer rounded-osce-lg border border-b2c-border bg-osce-surface p-4 transition-colors hover:bg-b2c-surface-muted"
      >
        <div className="flex flex-col items-center space-y-2.5 text-center">
          <div className="rounded-lg border border-b2c-border bg-b2c-surface-muted p-2.5">
            <HiOutlineCalendarDays className="h-4 w-4 text-b2c-text-secondary" />
          </div>
          <div>
            <h3 className="mb-0.5 text-osce-body font-semibold text-osce-ink-900">
              {schedulePracticeLabel}
            </h3>
            <p className="text-osce-meta text-b2c-text-muted">Practice at your convenience</p>
          </div>
          <div className="flex items-center gap-2 text-osce-accent transition-all duration-200 group-hover:gap-2.5">
            <span className="text-osce-body font-medium">{schedulePracticeActionLabel}</span>
            <HiOutlineArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </div>
        </div>
      </button>
    </div>
  );

  if (variant === "modal") {
    return (
      <div>
        <h2 className="mb-4 text-center font-heading text-osce-subheading font-semibold tracking-tight text-osce-ink-900">
          Choose practice option
        </h2>
        {content}
      </div>
    );
  }

  return (
    <div className="space-y-3 border-t border-b2c-border-light pt-5 sm:pt-6">
      <p className="px-4 text-center text-osce-meta uppercase tracking-wider text-b2c-text-muted">
        Or practice with colleagues via video call
      </p>
      {content}
    </div>
  );
}
