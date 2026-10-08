"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button, Input, Panel } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { formatMoney } from "@/foundation/format";
import {
  readPilotConfig,
  updatePilotConfig,
  type PilotConfig,
} from "@/capabilities/staff-growth/api";
import { formatRateForInput, formatThresholdsForInput, pilotUpdateFromForm } from "./pilotForm";

/** Internal only: the rate per visit and the spend-alert amounts. */
export function PilotConfigPanel({ partner }: { partner: string }) {
  const state = useAsync((signal) => readPilotConfig(partner, signal), [partner]);
  return (
    <Panel
      title="Pilot settings"
      description="Internal only. For now we guess spend from link visits until we can use BMJ's own click numbers."
    >
      <AsyncBoundary state={state}>
        {(config) => <PilotForm key={JSON.stringify(config)} partner={partner} initial={config} />}
      </AsyncBoundary>
    </Panel>
  );
}

function PilotForm({ partner, initial }: { partner: string; initial: PilotConfig }) {
  const [config, setConfig] = useState(initial);
  const [rate, setRate] = useState(formatRateForInput(initial.cost_per_click_pence));
  const [thresholds, setThresholds] = useState(
    formatThresholdsForInput(initial.spend_alert_thresholds_pence),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const save = async () => {
    setError(null);
    setSuccess(null);
    const update = pilotUpdateFromForm(rate, thresholds, config.spend_alert_thresholds_pence);
    if (!update) {
      setError("Enter a valid rate per visit.");
      return;
    }
    setSaving(true);
    try {
      setConfig(await updatePilotConfig(partner, update));
      setSuccess(
        update.reset_spend_alerts ? "Settings saved. Spend alert history was reset." : "Settings saved.",
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Input
          type="number"
          min="0"
          step="0.01"
          label="Rate per link visit (GBP)"
          value={rate}
          onChange={(event) => setRate(event.target.value)}
        />
        <div className="sm:col-span-2">
          <Input
            type="text"
            label="Email me when estimated spend reaches (GBP, comma-separated)"
            value={thresholds}
            placeholder="500, 1000, 2500"
            onChange={(event) => setThresholds(event.target.value)}
          />
        </div>
      </div>
      <p className="text-osce-caption text-ink-subtle">
        We&apos;re using {formatMoney(config.cost_per_click_pence)} per link visit for
        estimates. Alerts go to admin emails when estimated spend crosses one of those amounts.
      </p>
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {success ? <Alert tone="success">{success}</Alert> : null}
      <div className="flex justify-end">
        <Button type="button" onClick={() => save()} disabled={saving}>
          {saving ? "Saving…" : "Save settings"}
        </Button>
      </div>
    </div>
  );
}
