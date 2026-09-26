"use client";

import { useState, type FormEvent } from "react";
import {
  HiOutlineAdjustmentsHorizontal,
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineMicrophone,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Modal,
  ModalPrimaryButton,
  cn,
  productTokens,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { OnboardingFlow, rememberOnboardingSeen } from "@/capabilities/onboarding";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import TimerSettingsModal from "@/capabilities/account/settings/TimerSettingsModal";

const {
  b2cLink,
  b2cSettingsCardHeaderIcon,
  b2cSettingsCheckboxHelper,
  b2cSettingsCheckboxInput,
  b2cSettingsCheckboxRow,
  b2cSettingsCheckboxTitle,
  b2cSettingsIntro,
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
  const { code: examCode } = useCurrentExam();
  // Practice-only rows: peer practice and Athena's tour belong to a person's
  // own practice, not to an institution's workspace. The waiting-colleague
  // email was SCA-only in the old client (`appType === "sca"`).
  const practising = surface === "train";
  const isSca = practising && (me.exam_code ?? examCode) === "sca";

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
      setSuccessMessage("Preferences saved successfully");
    } catch {
      setError("Failed to save preferences");
    } finally {
      setSaving(false);
    }
  };

  const closeOnboarding = () => {
    rememberOnboardingSeen();
    setShowOnboarding(false);
  };

  return (
    <>
      <form onSubmit={(event) => void save(event)}>
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>
            <HiOutlineAdjustmentsHorizontal className={b2cSettingsCardHeaderIcon} aria-hidden />
            Preferences
          </B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-6 p-4 sm:p-6">
            <p className={b2cSettingsIntro}>
              Accessibility, AI consent, and notification settings for your account.
            </p>

            {successMessage ? <Alert message={successMessage} type="success" /> : null}
            {error ? <Alert message={error} type="error" /> : null}

            <div className="space-y-4">
              <label className={cn(b2cSettingsOptionRow, b2cSettingsCheckboxRow)}>
                <input
                  id="pref-dataConsentAI"
                  name="dataConsentAI"
                  type="checkbox"
                  checked={consent}
                  onChange={(event) => setConsent(event.target.checked)}
                  className={b2cSettingsCheckboxInput}
                />
                <span className="min-w-0">
                  <span className={b2cSettingsCheckboxTitle}>AI training consent</span>
                  <span className={b2cSettingsCheckboxHelper}>
                    Allow your data to be used for AI training to provide better personalized
                    recommendations and feedback.
                  </span>
                </span>
              </label>

              <div className={cn(b2cSettingsOptionRow, b2cSettingsCheckboxRow)}>
                <input
                  id="pref-needsExtraReadingTime"
                  name="needsExtraReadingTime"
                  type="checkbox"
                  checked={extraTime}
                  onChange={(event) => setExtraTime(event.target.checked)}
                  className={b2cSettingsCheckboxInput}
                />
                <div className="min-w-0 flex-1">
                  <label htmlFor="pref-needsExtraReadingTime" className={b2cSettingsCheckboxTitle}>
                    Extra reading time
                  </label>
                  <p className={b2cSettingsCheckboxHelper}>
                    I need extra time to support my neurodiverse learning needs.
                  </p>
                  <button
                    type="button"
                    onClick={() => setShowTimerSettings(true)}
                    className={cn("mt-3 text-osce-body", b2cLink, "underline")}
                  >
                    Configure your reading and simulation timers
                  </button>
                </div>
              </div>

              {isSca ? (
                <label className={cn(b2cSettingsOptionRow, b2cSettingsCheckboxRow)}>
                  <input
                    id="pref-notifyWhenPartnerWaiting"
                    name="notifyWhenPartnerWaiting"
                    type="checkbox"
                    checked={waitingEmail}
                    onChange={(event) => setWaitingEmail(event.target.checked)}
                    className={b2cSettingsCheckboxInput}
                  />
                  <span className="min-w-0">
                    <span className={b2cSettingsCheckboxTitle}>Email me when a colleague is waiting</span>
                    <span className={b2cSettingsCheckboxHelper}>
                      When a colleague&apos;s partner doesn&apos;t show for a marketplace session,
                      we&apos;ll email you so you can log in and join Live practice within 10 minutes.
                    </span>
                  </span>
                </label>
              ) : null}

              {practising ? (
                <div className={b2cSettingsOptionRow}>
                  <div className="min-w-0 flex-1">
                    <p className={b2cSettingsCheckboxTitle}>
                      <HiOutlineMicrophone
                        className="h-[18px] w-[18px] shrink-0 text-b2c-text-muted"
                        aria-hidden
                      />
                      Athena onboarding
                    </p>
                    <p className={b2cSettingsCheckboxHelper}>
                      Hear Athena introduce the app and try the voice demo again.
                    </p>
                    <button
                      type="button"
                      onClick={() => setShowOnboarding(true)}
                      className={cn("mt-3 text-osce-body", b2cLink, "underline")}
                    >
                      Walk through onboarding again
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </B2CPanelCardBody>
          <B2CPanelCardFooter className="px-4 pb-4 pt-8 sm:px-6 sm:pb-6">
            <ModalPrimaryButton type="submit" disabled={saving} className="gap-2">
              {saving ? (
                <>
                  <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden />
                  Saving…
                </>
              ) : (
                <>
                  <HiOutlineCheckCircle className="h-4 w-4" aria-hidden />
                  Save preferences
                </>
              )}
            </ModalPrimaryButton>
          </B2CPanelCardFooter>
        </B2CPanelCard>
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
          <OnboardingFlow onComplete={closeOnboarding} onSkip={closeOnboarding} />
        </Modal>
      ) : null}
    </>
  );
}
