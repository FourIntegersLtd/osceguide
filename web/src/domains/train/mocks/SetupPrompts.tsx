"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listPlans } from "@/capabilities/account/api";
import PlanPicker from "@/capabilities/account/settings/PlanPicker";

/** The old `PaymentsUpgrade` modal body: this exam's plans, on sale now. */
export function UpgradePlans({ examCode }: { examCode: string }) {
  const plans = useAsync((signal) => listPlans(signal), []);
  return (
    <AsyncBoundary state={plans}>
      {(page) => (
        <PlanPicker
          variant="modal"
          plans={page.items.filter((plan) => plan.exam_code === examCode)}
        />
      )}
    </AsyncBoundary>
  );
}
