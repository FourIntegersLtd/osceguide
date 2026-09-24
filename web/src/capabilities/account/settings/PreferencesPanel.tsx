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
 * Access arrangements and the three choices that used to sit beside them.
 *
 * Extra reading time is a percentage. AI-training consent, the waiting-email
 * nudge, and showing the guided tour again are stored on the account.
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
        {(me) => (
          <PreferencesForm
            key={me.id}
            initial={me.extra_reading_percent ?? 0}
            consent={me.ai_training_consent ?? false}
            waitingEmail={me.colleague_waiting_email ?? false}
            replay={me.replay_onboarding ?? false}
          />
        )}
      </AsyncBoundary>
    </SettingsTabShell>
  );
}

function PreferencesForm({
  initial,
  consent,
  waitingEmail,
  replay,
}: {
  initial: number;
  consent: boolean;
  waitingEmail: boolean;
  replay: boolean;
}) {
  const [percent, setPercent] = useState(initial);
  const [flags, setFlags] = useState({ consent, waitingEmail, replay });
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

      <PrefToggle
        checked={flags.consent}
        title="Allow my consultations to train OSCE Guide's models"
        detail="Off unless you turn it on. You can change this whenever you like."
        onChange={(checked) => void saveFlag("ai_training_consent", "consent", checked)}
      />
      <PrefToggle
        checked={flags.waitingEmail}
        title="Email me when a colleague is waiting to practise"
        detail="A note when someone is in the peer-practice queue for your exam."
        onChange={(checked) => void saveFlag("colleague_waiting_email", "waitingEmail", checked)}
      />
      <PrefToggle
        checked={flags.replay}
        title="Show the guided tour again"
        detail="The dashboard will offer the voice introduction the next time you open it."
        onChange={(checked) => void saveFlag("replay_onboarding", "replay", checked)}
      />
    </div>
  );

  async function saveFlag(
    field: "ai_training_consent" | "colleague_waiting_email" | "replay_onboarding",
    key: "consent" | "waitingEmail" | "replay",
    checked: boolean,
  ) {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await updateMe({ [field]: checked });
      setFlags((current) => ({ ...current, [key]: checked }));
      setSaved(true);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  }
}

function PrefToggle({
  checked,
  title,
  detail,
  onChange,
}: {
  checked: boolean;
  title: string;
  detail: string;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="mt-1 h-4 w-4 shrink-0"
      />
      <span>
        <span className="block text-osce-body text-osce-ink-900">{title}</span>
        <span className="block text-osce-meta text-b2c-text-muted">{detail}</span>
      </span>
    </label>
  );
}
