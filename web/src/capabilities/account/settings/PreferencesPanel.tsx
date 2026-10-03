"use client";

import { useState, type FormEvent } from "react";
import {
  HiOutlineClock,
  HiOutlineEnvelope,
  HiOutlineMicrophone,
  HiOutlineSparkles,
} from "react-icons/hi2";
import { AsyncBoundary, Button, Input, Modal } from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { OnboardingFlow, rememberOnboardingSeen } from "@/capabilities/onboarding";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { SettingsCard, SettingsRow, SettingsRows, Switch } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { describeTimer, formatTimer, parseTimer } from "@/capabilities/account/settings/timerFields";

/** What the timers open on for somebody with no custom timer: the SCA's own 3 and 12 minutes. */
const DEFAULT_READING_SECONDS = 3 * 60;
const DEFAULT_SIMULATION_SECONDS = 12 * 60;

/**
 * Access arrangements, AI consent and the waiting-colleague email.
 *
 * A card of switches and a card of the two custom timers, saved together with
 * one button (canvas `train-settings-prefs`). The timers apply to practice
 * whether or not "Extra reading time" is on.
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
      <AsyncBoundary state={state}>{(me) => <PreferencesForm key={me.id} me={me} />}</AsyncBoundary>
    </SettingsTabShell>
  );
}

function PreferencesForm({ me }: { me: Me }) {
  const { surface } = useSurface();
  const { settings, code: examCode } = useCurrentExam();
  const { session } = useSession();
  // Practice-only rows: peer practice and Athena's tour belong to a person's
  // own practice, not to an institution's workspace. The waiting-colleague
  // email is offered only where `settings.peer_waiting_email` says so.
  const practising = surface === "train";
  const offersWaitingEmail = practising && settings.peer_waiting_email;

  const [consent, setConsent] = useState(me.ai_training_consent ?? false);
  const [waitingEmail, setWaitingEmail] = useState(me.colleague_waiting_email ?? false);
  const [extraTime, setExtraTime] = useState(me.needs_extra_time ?? false);
  const [reading, setReading] = useState(formatTimer(me.custom_reading_seconds ?? DEFAULT_READING_SECONDS));
  const [simulation, setSimulation] = useState(
    formatTimer(me.custom_simulation_seconds ?? DEFAULT_SIMULATION_SECONDS),
  );
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");
  const [showOnboarding, setShowOnboarding] = useState(false);

  const readingSeconds = parseTimer(reading);
  const simulationSeconds = parseTimer(simulation);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setSuccessMessage("");
    if (readingSeconds === null || simulationSeconds === null) {
      setError("Enter each timer as minutes and seconds, such as 04:00, up to an hour.");
      return;
    }
    setSaving(true);
    try {
      await updateMe({
        ai_training_consent: consent,
        colleague_waiting_email: waitingEmail,
        needs_extra_time: extraTime,
        custom_reading_seconds: readingSeconds,
        custom_simulation_seconds: simulationSeconds,
      });
      setSuccessMessage("Preferences saved");
    } catch {
      setError("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  const closeOnboarding = () => {
    if (examCode && session?.user.id) rememberOnboardingSeen(examCode, session.user.id);
    setShowOnboarding(false);
  };

  return (
    <>
      <form onSubmit={(event) => void save(event)} className="space-y-6" noValidate>
        {successMessage ? <Alert message={successMessage} type="success" /> : null}
        {error ? <Alert message={error} type="error" /> : null}

        <SettingsCard title="Preferences" description="Accessibility, AI consent and notifications.">
          <SettingsRows>
            <SettingsRow
              icon={HiOutlineSparkles}
              title="AI training consent"
              meta="Let us use your consultations to improve our models"
              trailing={<Switch checked={consent} onChange={setConsent} label="AI training consent" />}
            />
            <SettingsRow
              icon={HiOutlineClock}
              title="Extra reading time"
              meta={
                readingSeconds !== null && simulationSeconds !== null
                  ? `Uses your own timers: ${describeTimer(readingSeconds)} reading, ${describeTimer(simulationSeconds)} consultation`
                  : "Uses your own timers"
              }
              trailing={<Switch checked={extraTime} onChange={setExtraTime} label="Extra reading time" />}
            />
            {offersWaitingEmail ? (
              <SettingsRow
                icon={HiOutlineEnvelope}
                title="Email me when a colleague is waiting"
                trailing={
                  <Switch
                    checked={waitingEmail}
                    onChange={setWaitingEmail}
                    label="Email me when a colleague is waiting"
                  />
                }
              />
            ) : null}
            {practising ? (
              <SettingsRow
                icon={HiOutlineMicrophone}
                title="Athena onboarding"
                meta="Walk through onboarding again"
                trailing={
                  <Button variant="secondary" size="sm" onClick={() => setShowOnboarding(true)}>
                    Start
                  </Button>
                }
              />
            ) : null}
          </SettingsRows>
        </SettingsCard>

        <SettingsCard title="Custom timer durations">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Reading timer (doctor information)"
              name="readingTimer"
              inputMode="numeric"
              placeholder="04:00"
              value={reading}
              onChange={(event) => setReading(event.target.value)}
              error={readingSeconds === null ? "Minutes and seconds, such as 04:00" : null}
            />
            <Input
              label="Simulation timer (consultation)"
              name="simulationTimer"
              inputMode="numeric"
              placeholder="14:00"
              value={simulation}
              onChange={(event) => setSimulation(event.target.value)}
              error={simulationSeconds === null ? "Minutes and seconds, such as 14:00" : null}
            />
          </div>
        </SettingsCard>

        <div className="flex justify-end">
          <Button type="submit" isLoading={saving}>
            Save preferences
          </Button>
        </div>
      </form>

      {showOnboarding ? (
        <Modal width="min(95vw, 560px)" height="fit-content" title="Athena onboarding" onClose={closeOnboarding}>
          <OnboardingFlow onComplete={closeOnboarding} />
        </Modal>
      ) : null}
    </>
  );
}
