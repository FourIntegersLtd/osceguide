"use client";

import { useState, type FormEvent } from "react";
import { HiOutlineMicrophone } from "react-icons/hi2";
import {
  AsyncBoundary,
  Button,
  Checkbox,
  Modal,
  Panel,
  cn,
  productTokens,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { OnboardingFlow, rememberOnboardingSeen } from "@/capabilities/onboarding";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import TimerSettingsModal from "@/capabilities/account/settings/TimerSettingsModal";

const {
  b2cLink,
  b2cSettingsCheckboxHelper,
  b2cSettingsCheckboxTitle,
  b2cSettingsOptionRow,
} = productTokens;

/** What the old modal opened on for somebody with no custom timer: the SCA's own 3 and 12 minutes. */
const DEFAULT_READING_SECONDS = 3 * 60;
const DEFAULT_SIMULATION_SECONDS = 12 * 60;

/**
 * Access arrangements, AI consent and the waiting-colleague email.
 *
 * The retiring client's Preferences card, row for row and string for string,
 * saved with one button. "Configure your reading and simulation timers" opens
 * the old minutes-and-seconds modal, which saves on its own; the timers only
 * apply while "Extra reading time" is ticked (`users.needs_extra_time`).
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
        {(me) => <PreferencesForm key={me.id} me={me} onTimersSaved={state.reload} />}
      </AsyncBoundary>
    </SettingsTabShell>
  );
}

function PreferencesForm({ me, onTimersSaved }: { me: Me; onTimersSaved: () => void }) {
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
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");
  const [showTimerSettings, setShowTimerSettings] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccessMessage("");
    try {
      await updateMe({
        ai_training_consent: consent,
        colleague_waiting_email: waitingEmail,
        needs_extra_time: extraTime,
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
      <form onSubmit={(event) => void save(event)}>
        <Panel title="Preferences" description="Accessibility, AI consent and notifications.">
          <div className="space-y-6">

            {successMessage ? <Alert message={successMessage} type="success" /> : null}
            {error ? <Alert message={error} type="error" /> : null}

            <div className="space-y-4">
              <Checkbox
                id="pref-dataConsentAI"
                name="dataConsentAI"
                checked={consent}
                onChange={(event) => setConsent(event.target.checked)}
                label="AI training consent"
                description="Allow your data to be used for AI training to provide better personalized recommendations and feedback."
              />

              <Checkbox
                id="pref-needsExtraReadingTime"
                name="needsExtraReadingTime"
                checked={extraTime}
                onChange={(event) => setExtraTime(event.target.checked)}
                label="Extra reading time"
                description={
                  <>
                    I need extra time to support my neurodiverse learning needs.
                    <button
                      type="button"
                      onClick={() => setShowTimerSettings(true)}
                      className={cn("mt-3 block text-osce-body", b2cLink, "underline")}
                    >
                      Configure your reading and simulation timers
                    </button>
                  </>
                }
              />

              {offersWaitingEmail ? (
                <Checkbox
                  id="pref-notifyWhenPartnerWaiting"
                  name="notifyWhenPartnerWaiting"
                  checked={waitingEmail}
                  onChange={(event) => setWaitingEmail(event.target.checked)}
                  label="Email me when a colleague is waiting"
                  description="When a colleague's partner doesn't show for a marketplace session, we'll email you so you can log in and join Live practice within 10 minutes."
                />
              ) : null}

              {practising ? (
                <div className={cn(b2cSettingsOptionRow, "items-center")}>
                  <div className="min-w-0 flex-1">
                    <p className={b2cSettingsCheckboxTitle}>
                      <HiOutlineMicrophone
                        className="h-[18px] w-[18px] shrink-0 text-ink-subtle"
                        aria-hidden
                      />
                      Athena onboarding
                    </p>
                    <p className={b2cSettingsCheckboxHelper}>
                      Walk through onboarding again: Athena introduces the app and the voice demo.
                    </p>
                  </div>
                  <Button type="button" variant="secondary" size="sm" onClick={() => setShowOnboarding(true)}>
                    Start
                  </Button>
                </div>
              ) : null}
            </div>
          </div>
          <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
            <Button type="submit" isLoading={saving}>
              Save preferences
            </Button>
          </div>
        </Panel>
      </form>

      {showTimerSettings ? (
        <TimerSettingsModal
          readingSeconds={me.custom_reading_seconds ?? DEFAULT_READING_SECONDS}
          simulationSeconds={me.custom_simulation_seconds ?? DEFAULT_SIMULATION_SECONDS}
          needsExtraTime={extraTime}
          onError={setError}
          onSuccess={(message) => {
            setSuccessMessage(message);
            onTimersSaved();
          }}
          onClose={() => setShowTimerSettings(false)}
        />
      ) : null}

      {showOnboarding ? (
        <Modal width="min(95vw, 560px)" height="fit-content" title="Athena onboarding" onClose={closeOnboarding}>
          <OnboardingFlow onComplete={closeOnboarding} />
        </Modal>
      ) : null}
    </>
  );
}
