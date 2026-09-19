"use client";

import { useState } from "react";
import { LuReceipt } from "react-icons/lu";
import { AsyncBoundary, Button } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { listBillingEvents } from "@/domains/platform/support/api";
import { RowList } from "@/domains/platform/chrome";
import { EventRow } from "@/domains/platform/user/BillingTab";

/** The webhook ledger; refused deliveries first, because they are the queue. */
export function BillingQueue() {
  const [failedOnly, setFailedOnly] = useState(true);
  const state = useAsync((signal) => listBillingEvents({ failedOnly, limit: 100 }, signal), [failedOnly]);
  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Billing"
        description="Stripe deliveries that were recorded and refused — paid, no access — and the rest of the ledger."
        icon={LuReceipt}
        actions={
          <Button variant="secondary" size="sm" onClick={() => setFailedOnly((v) => !v)}>
            {failedOnly ? "Show every delivery" : "Show refused only"}
          </Button>
        }
      />
      <AsyncBoundary state={state} isEmpty={(p) => p.items.length === 0} empty={{ title: "Nothing to reconcile", description: "Every delivery was applied." }}>
        {(page) => (
          <RowList>
            {page.items.map((event) => (
              <EventRow key={event.event_id} event={event} onChanged={state.reload} />
            ))}
          </RowList>
        )}
      </AsyncBoundary>
    </div>
  );
}
