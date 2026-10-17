"use client";

import { useState } from "react";
import {
  B2CSegmentedTabs,
  B2CPageHeader,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { BillingEvents } from "@/domains/platform/billing/BillingEvents";
import { PlansPanel } from "@/domains/platform/billing/PlansPanel";

type DeliveryFilter = "refused" | "all";

const DELIVERY_TABS: B2CSegmentedTabItem<DeliveryFilter>[] = [
  { id: "refused", label: "Refused" },
  { id: "all", label: "Every payment update" },
];

/** What the platform sells, then the webhook ledger; refused deliveries first, because they are the queue. */
export function BillingQueue() {
  const [filter, setFilter] = useState<DeliveryFilter>("refused");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Billing"
        subtitle="Plans on sale and payment updates from Stripe. Failed ones come first."
      />
      <PlansPanel />
      <BillingEvents
        title="Payment updates from Stripe"
        description="A failed update means someone paid but did not get access. Fix the problem, then try it again."
        failedOnly={filter === "refused"}
        actions={
          <B2CSegmentedTabs
            items={DELIVERY_TABS}
            value={filter}
            onChange={setFilter}
            compact
            aria-label="Payment updates shown"
          />
        }
        empty={
          filter === "refused"
            ? {
                title: "Nothing to reconcile",
                description: "Every payment gave access.",
              }
            : {
                title: "No payment updates",
                description: "No payments have come in from Stripe yet.",
              }
        }
      />
    </div>
  );
}
