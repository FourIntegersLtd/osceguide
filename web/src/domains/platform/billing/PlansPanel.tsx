"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  Badge,
  Button,
  ConfirmModal,
  Input,
  Modal,
  Select,
} from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listExams } from "@/capabilities/stations";
import { validationFields } from "@/foundation/platform-client/errors";
import {
  createPlatformPlan,
  listPlatformPlans,
  updatePlatformPlan,
  type PlatformPlan,
} from "@/domains/platform/support/api";
import { FREE_TRIAL_STATIONS } from "@/foundation/config/copyNumbers";

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
  // Retiring stops new sales, so it asks first; putting a plan back on sale does not.
  const [retiring, setRetiring] = useState<PlatformPlan | null>(null);
  const [settingStations, setSettingStations] = useState<PlatformPlan | null>(null);

  const toggle = async (plan: PlatformPlan) => {
    setBusyCode(plan.code);
    setError(null);
    try {
      await updatePlatformPlan(plan.code, { active: !plan.active });
      toast.success(
        plan.active ? `${plan.code} is off sale` : `${plan.code} is on sale`,
      );
      plans.reload();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusyCode(null);
      setRetiring(null);
    }
  };

  const saveStationLimit = async (plan: PlatformPlan, value: number | null) => {
    setBusyCode(plan.code);
    setError(null);
    try {
      await updatePlatformPlan(plan.code, { station_limit: value });
      toast.success(
        value === null
          ? `${plan.code} now unlocks every station`
          : `${plan.code} now unlocks ${value} stations`,
      );
      plans.reload();
    } catch (cause) {
      // A refused body names the field and the reason; show them, not just "not valid".
      const reasons = Object.entries(validationFields(cause)).map(([field, reason]) => `${field}: ${reason}`);
      setError(reasons.length > 0 ? reasons.join(". ") : errorMessage(cause));
    } finally {
      setBusyCode(null);
      setSettingStations(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button themeType="b2b" variant="commit" size="sm" onClick={() => setCreating(true)}>
          New price
        </Button>
      </div>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      <AsyncBoundary state={plans}>
        {(page) => (
          <Table<PlatformPlan>
            rows={page.items}
            themeType="b2b"
            idField="code"
            title="Prices"
            description="Each plan is sold at full price, or at 10% off with a referral code. Both prices are set up in Stripe for you."
            empty={{
              title: "Nothing is on sale",
              description: "Add a price for a published exam.",
            }}
            columns={[
              {
                header: "Plan",
                key: "code",
                priority: "primary",
                render: (plan) => (
                  <div className="min-w-0">
                    <p className="font-medium text-ink">
                      {plan.exam_code} · {pounds(plan.amount_pence)} for {plan.duration_days} days
                    </p>
                    <p className="truncate text-osce-meta text-ink-subtle">
                      {plan.code}
                      {plan.referral_amount_pence != null
                        ? ` · ${pounds(plan.referral_amount_pence)} with a referral code`
                        : ""}
                      {` · ${plan.stripe_price_id}`}
                    </p>
                  </div>
                ),
              },
              {
                header: "Status",
                key: "active",
                render: (plan) => (
                  <Badge tone={plan.active ? "success" : "neutral"} dot>
                    {plan.active ? "On sale" : "Retired"}
                  </Badge>
                ),
              },
              {
                header: "Stations",
                key: "station_limit",
                render: (plan) => (
                  <span className="text-ink">
                    {plan.station_limit ?? "No limit"}
                  </span>
                ),
              },
              {
                header: "",
                key: "stripe_price_id",
                render: (plan) => (
                  <div className="flex gap-2">
                    <Button
                      themeType="b2b"
                      size="sm"
                      variant="secondary"
                      disabled={busyCode !== null}
                      onClick={() => setSettingStations(plan)}
                    >
                      Set stations
                    </Button>
                    <Button
                      themeType="b2b"
                      size="sm"
                      variant="secondary"
                      disabled={busyCode !== null}
                      onClick={() => (plan.active ? setRetiring(plan) : toggle(plan))}
                    >
                      {busyCode === plan.code
                        ? "Saving…"
                        : plan.active
                          ? "Retire"
                          : "Put on sale"}
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        )}
      </AsyncBoundary>
      <ConfirmModal
        isOpen={retiring !== null}
        title="Take this price off sale?"
        message={
          retiring
            ? `Take ${retiring.code} (${retiring.exam_code} · ${pounds(retiring.amount_pence)}) off sale? New buyers can no longer choose it. Existing subscribers keep their access.`
            : ""
        }
        confirmText="Retire"
        tone="danger"
        onCancel={() => setRetiring(null)}
        onConfirm={() => (retiring ? toggle(retiring) : undefined)}
      />
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
      {settingStations ? (
        <StationLimitModal
          plan={settingStations}
          busy={busyCode === settingStations.code}
          onClose={() => setSettingStations(null)}
          onSave={(value) => saveStationLimit(settingStations, value)}
        />
      ) : null}
    </div>
  );
}

function StationLimitModal({
  plan,
  busy,
  onClose,
  onSave,
}: {
  plan: PlatformPlan;
  busy: boolean;
  onClose: () => void;
  onSave: (value: number | null) => void;
}) {
  const [value, setValue] = useState(plan.station_limit?.toString() ?? "");
  const [error, setError] = useState<string | null>(null);

  const valid = value === "" || (/^[0-9]+$/.test(value) && Number(value) >= 1 && Number(value) <= 10000);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!valid) return;
    setError(null);
    try {
      onSave(value === "" ? null : Number(value));
    } catch (cause) {
      setError(errorMessage(cause));
    }
  };

  return (
    <Modal onClose={onClose} title={`Stations for ${plan.code}`} width="min(28rem, 96vw)">
      <form onSubmit={submit} className="flex flex-col gap-3 p-4 lg:p-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Input
          label="Stations this plan unlocks"
          type="number"
          min="1"
          max="10000"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          disabled={busy}
          hint={`Include the ${FREE_TRIAL_STATIONS} free trial stations. Leave empty for no limit.`}
        />
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !valid}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
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
  const [stationLimit, setStationLimit] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const amountPence = Math.round(Number(price) * 100);
  const validStationLimit =
    stationLimit === "" ||
    (/^[0-9]+$/.test(stationLimit) && Number(stationLimit) >= 1 && Number(stationLimit) <= 10000);
  const valid =
    examCode !== "" &&
    /^[a-z0-9][a-z0-9_]{1,22}$/.test(code) &&
    amountPence >= 100 &&
    Number(days) >= 1 &&
    validStationLimit;

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
          station_limit: stationLimit === "" ? null : Number(stationLimit),
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
        <Select
          label="Exam"
          value={examCode}
          onChange={(event) => {
            setExamCode(event.target.value);
            if (!code)
              setCode(
                `${event.target.value}_${Math.round(Number(days) / 30) || 1}m`,
              );
          }}
          disabled={busy}
        >
          <option value="">Choose a published exam</option>
          {(exams.data?.items ?? []).map((exam) => (
            <option key={exam.code} value={exam.code}>
              {exam.name} ({exam.code})
            </option>
          ))}
        </Select>
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
          hint="A short internal name using lowercase letters, numbers and underscores, such as sca_one_month. It cannot be reused."
          autoComplete="off"
        />
        <Input
          label="Stations this plan unlocks"
          type="number"
          min="1"
          max="10000"
          value={stationLimit}
          onChange={(event) => setStationLimit(event.target.value)}
          disabled={busy}
          hint={`Include the ${FREE_TRIAL_STATIONS} free trial stations. Leave empty for no limit.`}
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
