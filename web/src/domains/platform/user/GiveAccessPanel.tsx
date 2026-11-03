"use client";

import { useRef, useState } from "react";
import { Alert, Button, Checkbox, Input, Panel, Select } from "@/foundation/ui";
import { errorMessage, useToast, type AsyncState } from "@/foundation/hooks";
import {
  recordManualPayment,
  type PlatformExamAccess,
  type PlatformPlan,
} from "@/domains/platform/support/api";
import { penceFrom, poundsLabel } from "@/domains/platform/support/money";
import { giveAccessLabel, hasPlanToQueueBehind, planName } from "@/domains/platform/user/accessCopy";

/** Gives access by choosing a plan. A blank amount is a free place. One button, no second confirm. */
export function GiveAccessPanel({
  userId,
  email,
  plans,
  accessRows,
  onGiven,
}: {
  userId: string;
  email: string;
  plans: AsyncState<{ items: PlatformPlan[] }>;
  accessRows: PlatformExamAccess[];
  onGiven: () => void;
}) {
  const toast = useToast();
  // A pick list of the real plans, on sale first: typing a code invited a guess that matched no plan.
  const choices = [...(plans.data?.items ?? [])].sort(
    (first, second) => Number(second.active) - Number(first.active) || first.code.localeCompare(second.code),
  );
  const [planCode, setPlanCode] = useState("");
  const [amount, setAmount] = useState("");
  const [start, setStart] = useState<"now" | "after_current">("after_current");
  const [sendReceipt, setSendReceipt] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Kept across a failed try and sent with every try, so a double click or a retry grants once.
  // A new one is made only after a success.
  const reference = useRef(`manual:${crypto.randomUUID()}`);
  const inFlight = useRef(false);

  const chosenPlan = choices.find((plan) => plan.code === planCode);
  const pence = penceFrom(amount);
  const amountInvalid = amount.trim() !== "" && pence === null;
  const hasAmount = pence !== null && pence > 0;
  // "When it starts" is only a question when they already have a bought plan on this exam.
  const asksStart = hasPlanToQueueBehind(
    accessRows.find((row) => row.exam_code === chosenPlan?.exam_code),
    new Date(),
  );

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (inFlight.current) return;
    if (amountInvalid) {
      setError("Enter the amount as a number of pounds, such as 12 or 12.50.");
      return;
    }
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      const emailReceipt = hasAmount && sendReceipt;
      await recordManualPayment(userId, {
        planCode,
        reference: reference.current,
        amountPence: pence,
        sendReceipt: emailReceipt,
        start: asksStart ? start : "now",
        note: note.trim(),
      });
      toast.success("Access given", emailReceipt ? `A receipt was emailed to ${email}.` : "No receipt was emailed.");
      reference.current = `manual:${crypto.randomUUID()}`;
      setNote("");
      setAmount("");
      onGiven();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Give access"
      description="Choose a plan. Leave the amount blank for a free place, such as a bank transfer, a sponsor or a goodwill month."
      padding="sm"
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {plans.error ? <Alert tone="danger">Could not load the plans: {errorMessage(plans.error)}</Alert> : null}
        <Select
          label="Plan"
          value={planCode}
          onChange={(event) => setPlanCode(event.target.value)}
          disabled={busy || plans.loading}
          required
        >
          <option value="">{plans.loading ? "Loading plans…" : "Choose a plan"}</option>
          {choices.map((plan) => (
            <option key={plan.code} value={plan.code}>
              {`${planName(plan)} · ${poundsLabel(plan.amount_pence)}${plan.active ? "" : " · retired"}`}
            </option>
          ))}
        </Select>
        <Input
          label="Amount paid"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          disabled={busy}
          hint="In pounds. Leave it blank for a free place."
          inputMode="decimal"
        />
        {asksStart ? (
          <fieldset className="flex flex-col gap-2" disabled={busy}>
            <legend className="text-osce-meta text-ink-muted">When it starts</legend>
            <label className="flex items-center gap-2 text-osce-data text-ink">
              <input
                type="radio"
                name="start"
                checked={start === "after_current"}
                onChange={() => setStart("after_current")}
                className="accent-accent"
              />
              Starts when the current plan ends
            </label>
            <label className="flex items-center gap-2 text-osce-data text-ink">
              <input
                type="radio"
                name="start"
                checked={start === "now"}
                onChange={() => setStart("now")}
                className="accent-accent"
              />
              Starts now
            </label>
          </fieldset>
        ) : null}
        {hasAmount ? (
          <Checkbox
            label="Email a receipt"
            checked={sendReceipt}
            onChange={(event) => setSendReceipt(event.target.checked)}
            disabled={busy}
          />
        ) : null}
        <Input
          label="Why"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={busy}
          required
          hint="Goes in the audit log."
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={busy || !chosenPlan || !note.trim()}>
            {busy ? "Saving…" : chosenPlan ? giveAccessLabel(chosenPlan, pence) : "Give access"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
