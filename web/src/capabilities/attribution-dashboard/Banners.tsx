"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { formatMoney } from "@/foundation/format";

function Note({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="flex gap-3 rounded-osce-lg border border-warning/25 bg-warning-subtle px-4 py-3 text-osce-meta text-ink"
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
    <Note title="Rough BMJ spend estimate (internal only)">
      {spend.billing_disclaimer} We&apos;re using{" "}
      <strong>{formatMoney(spend.cost_per_click_pence)}</strong> per link visit for this
      estimate.
    </Note>
  );
}
