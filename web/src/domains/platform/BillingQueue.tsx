"use client";

import { useState } from "react";
import { LuReceipt } from "react-icons/lu";
import {
  B2CSegmentedTabs,
  PlatformPageHeader,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { BillingEvents } from "@/domains/platform/billing/BillingEvents";
import { PlansPanel } from "@/domains/platform/billing/PlansPanel";

type DeliveryFilter = "refused" | "all";

const DELIVERY_TABS: B2CSegmentedTabItem<DeliveryFilter>[] = [
  { id: "refused", label: "Refused" },
  { id: "all", label: "Every delivery" },
];

/** What the platform sells, then the webhook ledger; refused deliveries first, because they are the queue. */
export function BillingQueue() {
  const [filter, setFilter] = useState<DeliveryFilter>("refused");

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Billing"
        description="Prices on sale, and every Stripe delivery — refused ones first, because paid with no access is the queue."
        icon={LuReceipt}
      />
      <PlansPanel />
      <BillingEvents
        title="Stripe deliveries"
        description="A refused delivery is money taken with no access given. Fix its cause, then replay it."
        failedOnly={filter === "refused"}
        actions={
          <B2CSegmentedTabs
            items={DELIVERY_TABS}
            value={filter}
            onChange={setFilter}
            compact
            aria-label="Deliveries shown"
          />
        }
        empty={
          filter === "refused"
            ? {
                title: "Nothing to reconcile",
                description: "Every delivery was applied.",
              }
            : {
                title: "No deliveries",
                description: "Stripe has sent nothing yet.",
              }
        }
      />
    </div>
  );
}
