"use client";

import { useState } from "react";
import { LuReceipt } from "react-icons/lu";
import { Button } from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { PlatformBillingEventsTable } from "@/domains/platform/billing/BillingEventsTable";
import { PlansPanel } from "@/domains/platform/billing/PlansPanel";

/** What the platform sells, then the webhook ledger; refused deliveries first, because they are the queue. */
export function BillingQueue() {
  const [failedOnly, setFailedOnly] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Billing"
        description="Prices on sale, then Stripe deliveries that were recorded and refused — paid, no access — and the rest of the ledger."
        icon={LuReceipt}
        actions={
          <Button variant="secondary" size="sm" onClick={() => setFailedOnly((v) => !v)}>
            {failedOnly ? "Show every delivery" : "Show refused only"}
          </Button>
        }
      />
      <PlansPanel />
      <PlatformBillingEventsTable
        key={`${failedOnly}-${reloadKey}`}
        failedOnly={failedOnly}
        onChanged={() => setReloadKey((k) => k + 1)}
        empty={{
          title: "Nothing to reconcile",
          description: "Every delivery was applied.",
        }}
      />
    </div>
  );
}
