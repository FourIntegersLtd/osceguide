"use client";

import { b2cCard, b2cCardPadding, b2cGhostButton } from "@/foundation/ui/productTokens";

/** What the marketplace is, said once at the top; the exam is named by the backend. */
export function MarketplaceIntroCard({
  examName,
  onLearnMore,
}: {
  examName: string | null;
  onLearnMore: () => void;
}) {
  const examLabel = examName ?? "same";
  return (
    <div
      className={`${b2cCard} ${b2cCardPadding} bg-gradient-to-br from-osce-accent-muted/90 to-b2c-surface`}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <h2 className="text-osce-body font-semibold text-osce-ink-900">
            Colleague Video Sessions
          </h2>
          <p className="text-osce-body leading-relaxed text-b2c-text-secondary">
            Through the marketplace, you can practice with colleagues preparing for the{" "}
            {examLabel} exam via live video calls. Post your availability or claim someone
            else&apos;s slot and get matched with doctors across the country.
          </p>
        </div>
        <button
          type="button"
          onClick={onLearnMore}
          className={`w-full shrink-0 sm:w-auto ${b2cGhostButton}`}
        >
          Learn how it works
        </button>
      </div>
    </div>
  );
}
