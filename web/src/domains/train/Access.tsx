"use client";

import { LuCircleCheck, LuReceipt } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listEntitlements, listPlans, listReceipts } from "@/domains/train/api";

/**
 * What you can practise, why, and until when.
 *
 * An entitlement carries its source, so "my institution gave me this" and "I
 * bought this" are visibly different things. A payment does not *mean* access;
 * it granted it, and a refund revokes the grant while the payment record
 * stands — which is why these are two lists rather than one.
 */
export function Access() {
  const entitlements = useAsync((signal) => listEntitlements(signal), []);
  const plans = useAsync((signal) => listPlans(signal), []);
  const receipts = useAsync((signal) => listReceipts(signal), []);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Your access" description="What you can practise, and until when." />

      <AsyncBoundary state={entitlements}>
        {(data) => (
          <Card title="Active access">
            {data.items.length === 0 ? (
              <p className="text-sm text-ink-muted">
                You have no access yet. A free trial covers a few stations so you can decide.
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {data.items.map((entitlement) => (
                  <li
                    key={`${entitlement.exam_code}-${entitlement.source}`}
                    className="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-ink">
                        {entitlement.exam_code.toUpperCase()}
                      </p>
                      <p className="text-xs capitalize text-ink-subtle">
                        from your {entitlement.source}
                        {entitlement.ends_at
                          ? ` · until ${new Date(entitlement.ends_at).toLocaleDateString()}`
                          : ""}
                      </p>
                    </div>
                    {entitlement.live ? (
                      <Badge tone="success">
                        <LuCircleCheck className="mr-1 h-3 w-3" aria-hidden /> Active
                      </Badge>
                    ) : (
                      <Badge tone="neutral">Ended</Badge>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}
      </AsyncBoundary>

      <AsyncBoundary state={plans}>
        {(page) => (
          <Card title="Plans" description="What access costs.">
            <div className="flex flex-col gap-4">
              <ul className="grid gap-3 sm:grid-cols-2">
                {page.items.map((plan) => (
                  <li
                    key={plan.code}
                    className="rounded-panel border border-border p-4"
                  >
                    <p className="text-sm font-medium text-ink">
                      {plan.exam_code ? plan.exam_code.toUpperCase() : "All exams"}
                    </p>
                    <p className="mt-1 text-2xl font-semibold text-ink">
                      {formatMoney(plan.amount_pence, plan.currency)}
                    </p>
                    <p className="text-sm text-ink-muted">
                      {plan.duration_days} days of access
                    </p>
                  </li>
                ))}
              </ul>
              {/* Honest rather than a button that does nothing: the backend has
                  plans and a Stripe webhook, but no checkout-session route yet. */}
              <Alert tone="info">
                Buying online is not switched on yet. Get in touch and we will set your access up.
              </Alert>
            </div>
          </Card>
        )}
      </AsyncBoundary>

      <AsyncBoundary state={receipts}>
        {(data) =>
          data.items.length === 0 ? (
            <></>
          ) : (
            <Card title="Receipts">
              <ul className="divide-y divide-border">
                {data.items.map((receipt, index) => (
                  <li
                    key={`${receipt.paid_at}-${index}`}
                    className="flex flex-wrap items-center justify-between gap-3 py-3"
                  >
                    <span className="flex items-center gap-2 text-sm text-ink">
                      <LuReceipt className="h-3.5 w-3.5 text-ink-subtle" aria-hidden />
                      {receipt.plan_label}
                    </span>
                    <span className="text-sm text-ink-muted">
                      {receipt.amount_total} {receipt.currency.toUpperCase()} ·{" "}
                      {new Date(receipt.paid_at).toLocaleDateString()}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          )
        }
      </AsyncBoundary>
    </div>
  );
}

function formatMoney(pence: number, currency: string): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: currency.toUpperCase(),
  }).format(pence / 100);
}
