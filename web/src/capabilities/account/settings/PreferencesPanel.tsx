"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Button, cn, productTokens } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { readMe, updateMe } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cInputBase } = productTokens;

/** What a bare "yes, I need extra time" used to mean in the old client. */
const STANDARD_EXTRA = 25;

/**
 * Access arrangements.
 *
 * One field, where the retiring tab had four. The other three — AI training
 * consent, "email me when a colleague is waiting", and replaying the tutor's
 * onboarding — have nowhere to be stored, and a checkbox that cannot save is
 * worse than no checkbox. They are in `docs/port-gaps.md`.
 *
 * Extra reading time is a percentage rather than the old boolean, because a
 * percentage says what was actually granted; the old client carried a bare
 * flag and applied a fixed amount inside the timer component.
 *
 * It applies to a person's own practice only. An institution's circuit runs on
 * one clock for everybody on it, and stretching it for one candidate would
 * stretch it for the rest — so an accommodation in an examination hall is made
 * to the circuit's timing, by whoever runs it.
 */
export default function PreferencesPanel() {
  const state = useAsync((signal) => readMe(signal), []);

  return (
    <SettingsTabShell>
      <AsyncBoundary state={state}>
        {(me) => <PreferencesForm key={me.id} initial={me.extra_reading_percent ?? 0} />}
      </AsyncBoundary>
    </SettingsTabShell>
  );
}

function PreferencesForm({ initial }: { initial: number }) {
  const [percent, setPercent] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = async (value: number) => {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await updateMe({ extra_reading_percent: value });
      setPercent(value);
      setSaved(true);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {error && <Alert tone="danger">{error}</Alert>}
      {saved && <Alert tone="success">Saved.</Alert>}

      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={percent > 0}
          onChange={(event) => void save(event.target.checked ? STANDARD_EXTRA : 0)}
          disabled={saving}
          className="mt-1 h-4 w-4 shrink-0"
        />
        <span>
          <span className="block text-osce-body text-osce-ink-900">
            I am granted extra reading time
          </span>
          <span className="block text-osce-meta text-b2c-text-muted">
            Your reading period is extended by this much in your own practice.
          </span>
        </span>
      </label>

      {percent > 0 && (
        <div>
          <label htmlFor="extra-reading-percent" className={b2cFieldLabel}>
            Extra reading time
          </label>
          <div className="mt-1.5 flex items-center gap-2">
            <input
              id="extra-reading-percent"
              type="number"
              min={1}
              max={100}
              value={percent}
              onChange={(event) => setPercent(Number(event.target.value))}
              className={cn(b2cInputBase, "w-28")}
            />
            <span className="text-osce-body text-b2c-text-muted">%</span>
            <Button
              type="button"
              variant="secondary"
              size="md"
              onClick={() => void save(percent)}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
