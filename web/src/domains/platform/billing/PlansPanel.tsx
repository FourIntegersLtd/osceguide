"use client";

import { useState } from "react";
import { Alert, Badge, Button, Card, Input, Modal } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listExams } from "@/capabilities/stations";
import {
  createPlatformPlan,
  listPlatformPlans,
  setPlatformPlanActive,
  type PlatformPlan,
} from "@/domains/platform/support/api";

const pounds = (pence: number) => `£${(pence / 100).toFixed(2)}`;

/**
 * What the platform sells. A price never changes once written — every payment
 * names it — so a new price is a new plan and the old one is retired. Retiring
 * stops new checkouts only; a payment already under way is still granted.
 */
export function PlansPanel() {
  const toast = useToast();
  const plans = useAsync((signal) => listPlatformPlans(signal), []);
  const [creating, setCreating] = useState(false);
  const [busyCode, setBusyCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toggle = async (plan: PlatformPlan) => {
    setBusyCode(plan.code);
    setError(null);
    try {
      await setPlatformPlanActive(plan.code, !plan.active);
      toast.success(
        plan.active ? `${plan.code} is off sale` : `${plan.code} is on sale`,
      );
      plans.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyCode(null);
    }
  };

  const items = plans.data?.items ?? [];

  return (
    <Card
      padding="md"
      title="Prices"
      description="Each plan is sold at full price and, with a referral code, at 10% off. Stripe prices are created for you."
      actions={
        <Button size="sm" onClick={() => setCreating(true)}>
          New price
        </Button>
      }
    >
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {plans.error ? (
        <Alert tone="danger">{errorMessage(plans.error)}</Alert>
      ) : plans.loading && !plans.data ? (
        <p className="text-osce-data text-b2c-text-muted">Loading prices…</p>
      ) : items.length === 0 ? (
        <p className="text-osce-data text-b2c-text-muted">
          Nothing is on sale yet. Add a price for a published exam.
        </p>
      ) : (
        <ul className="divide-y divide-b2c-border">
          {items.map((plan) => (
            <li
              key={plan.code}
              className="flex flex-wrap items-center justify-between gap-3 py-3"
            >
              <div className="min-w-0">
                <p className="font-medium text-osce-ink-900">
                  {plan.exam_code} · {pounds(plan.amount_pence)} for{" "}
                  {plan.duration_days} days
                </p>
                <p className="truncate text-osce-meta text-b2c-text-muted">
                  {plan.code}
                  {plan.referral_amount_pence != null
                    ? ` · ${pounds(plan.referral_amount_pence)} with a referral code`
                    : ""}
                  {` · ${plan.stripe_price_id}`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={plan.active ? "success" : "neutral"}>
                  {plan.active ? "On sale" : "Retired"}
                </Badge>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={busyCode !== null}
                  onClick={() => void toggle(plan)}
                >
                  {busyCode === plan.code
                    ? "Saving…"
                    : plan.active
                      ? "Retire"
                      : "Put on sale"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {creating ? (
        <NewPlanModal
          onClose={() => setCreating(false)}
          onCreated={(plan) => {
            toast.success(
              `${plan.code} is on sale`,
              `${pounds(plan.amount_pence)} for ${plan.duration_days} days`,
            );
            setCreating(false);
            plans.reload();
          }}
        />
      ) : null}
    </Card>
  );
}

function NewPlanModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (plan: PlatformPlan) => void;
}) {
  // The public catalogue: only a published platform exam can be sold.
  const exams = useAsync((signal) => listExams(signal), []);
  const [examCode, setExamCode] = useState("");
  const [code, setCode] = useState("");
  const [price, setPrice] = useState("");
  const [days, setDays] = useState("30");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const amountPence = Math.round(Number(price) * 100);
  const valid =
    examCode !== "" &&
    /^[a-z0-9][a-z0-9_]{1,22}$/.test(code) &&
    amountPence >= 100 &&
    Number(days) >= 1;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onCreated(
        await createPlatformPlan({
          exam_code: examCode,
          code,
          amount_pence: amountPence,
          duration_days: Number(days),
        }),
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal onClose={onClose} title="New price" width="min(32rem, 96vw)">
      <form onSubmit={submit} className="flex flex-col gap-3 p-4 lg:p-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {exams.error ? (
          <Alert tone="danger">
            Could not load the exams: {errorMessage(exams.error)}
          </Alert>
        ) : null}
        <label className="flex flex-col gap-1 text-osce-meta font-medium text-osce-ink-700">
          Exam
          <select
            value={examCode}
            onChange={(event) => {
              setExamCode(event.target.value);
              if (!code)
                setCode(
                  `${event.target.value}_${Math.round(Number(days) / 30) || 1}m`,
                );
            }}
            disabled={busy}
            className="rounded-md border border-b2c-border bg-white px-3 py-2 text-osce-body text-osce-ink-900"
          >
            <option value="">Choose a published exam</option>
            {(exams.data?.items ?? []).map((exam) => (
              <option key={exam.code} value={exam.code}>
                {exam.name} ({exam.code})
              </option>
            ))}
          </select>
        </label>
        <Input
          label="Price (£)"
          type="number"
          min="1"
          step="0.01"
          required
          value={price}
          onChange={(event) => setPrice(event.target.value)}
          disabled={busy}
          hint={
            amountPence >= 100
              ? `With a referral code: ${pounds(Math.floor((amountPence * 90) / 100))}`
              : undefined
          }
        />
        <Input
          label="Access (days)"
          type="number"
          min="1"
          max="730"
          required
          value={days}
          onChange={(event) => setDays(event.target.value)}
          disabled={busy}
        />
        <Input
          label="Plan code"
          required
          value={code}
          onChange={(event) => setCode(event.target.value.toLowerCase())}
          disabled={busy}
          hint="Lowercase letters, digits and underscores; never reused. e.g. sca_1m"
          autoComplete="off"
        />
        <div className="flex justify-end gap-2 pt-1">
          <Button
            type="button"
            variant="ghost"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !valid}>
            {busy ? "Creating in Stripe…" : "Create price"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
