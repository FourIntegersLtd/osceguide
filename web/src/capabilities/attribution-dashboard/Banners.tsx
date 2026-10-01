"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { formatMoney } from "@/foundation/format";

function Note({
  tone,
  title,
  children,
}: {
  tone: "warning" | "neutral";
  title: string;
  children: React.ReactNode;
}) {
  const classes =
    tone === "warning"
      ? "border-warning/25 bg-warning-subtle text-ink"
      : "border-border bg-canvas text-ink-muted";
  return (
    <div
      className={`flex gap-3 rounded-osce-lg border px-4 py-3 text-osce-meta ${classes}`}
      role="note"
    >
      <HiOutlineInformationCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div>
        <p className="font-medium text-ink">{title}</p>
        <p className="mt-1">{children}</p>
      </div>
    </div>
  );
}

/** Staff only: the spend is a guess from visits, and this says so. Nothing shows until spend exists. */
export function SpendDisclaimerBanner({
  spend,
}: {
  spend: { billing_disclaimer: string; cost_per_click_pence: number } | null | undefined;
}) {
  if (!spend) return null;
  return (
    <Note tone="warning" title="Rough BMJ spend estimate (internal only)">
      {spend.billing_disclaimer} We&apos;re using{" "}
      <strong>{formatMoney(spend.cost_per_click_pence)}</strong> per link visit for this
      estimate.
    </Note>
  );
}

/** A partner's reminder that the fee is a guide and not a bill. */
export function FeeDisclaimerBanner({
  fee,
}: {
  fee: { billing_disclaimer: string; cost_per_click_pence: number } | null | undefined;
}) {
  if (!fee) {
    return (
      <Note tone="neutral" title="Fee estimates are a guide only">
        The fee shown here is an estimate from our arrival counts. You invoice from your own
        click records; nothing on this page is a bill.
      </Note>
    );
  }
  return (
    <Note tone="warning" title="Estimated fee (guide only)">
      {fee.billing_disclaimer} We&apos;re using{" "}
      <strong>{formatMoney(fee.cost_per_click_pence)}</strong> per link visit.
    </Note>
  );
}
