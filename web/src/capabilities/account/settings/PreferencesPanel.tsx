"use client";

import { useState } from "react";
import {
  HiOutlineClock,
  HiOutlineEnvelope,
  HiOutlineMicrophone,
  HiOutlineSparkles,
} from "react-icons/hi2";
import { AsyncBoundary, Button, Input, Modal, Panel } from "@/foundation/ui";
import { useAsync, useToast } from "@/foundation/hooks";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { OnboardingFlow, rememberOnboardingSeen } from "@/capabilities/onboarding";
import { readMe, updateMe, type Me } from "@/capabilities/account/api";
import {
  preferencePatch,
  type PracticeTimers,
  type PreferenceField,
} from "@/capabilities/account/settings/preferencesModel";
import { SettingsRow, SettingsRows, Switch } from "@/capabilities/account/settings/SettingsKit";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";
import { describeTimer, formatTimer, parseTimer } from "@/capabilities/account/settings/timerFields";

/** What the timers open on for somebody with no custom timer: the SCA's own 3 and 12 minutes. */
const DEFAULT_READING_SECONDS = 3 * 60;
const DEFAULT_SIMULATION_SECONDS = 12 * 60;

/**
 * Access arrangements, AI consent and the waiting-colleague email.
 *
 * A card of switches (canvas `train-settings-prefs`). Each switch saves as it
 * changes, sending only its own field (`preferencePatch`); the switch is the
 * feedback, and a failed save puts it back and says so. Turning "Extra reading
 * time" on opens a modal for the two custom timers and saves when they are
 * confirmed; they apply to practice only while it is on.
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

  const [prefs, setPrefs] = useState<Record<PreferenceField, boolean>>({
    ai_training_consent: me.ai_training_consent ?? false,
    colleague_waiting_email: me.colleague_waiting_email ?? false,
    needs_extra_time: me.needs_extra_time ?? false,
  });
  const setPref = (field: PreferenceField, value: boolean) => setPrefs((now) => ({ ...now, [field]: value }));
  const [timers, setTimers] = useState<PracticeTimers>({
    readingSeconds: me.custom_reading_seconds ?? DEFAULT_READING_SECONDS,
    simulationSeconds: me.custom_simulation_seconds ?? DEFAULT_SIMULATION_SECONDS,
  });
  /** Fields being saved: each switch is disabled until its own save answers, so a double click is one save. */
  const [saving, setSaving] = useState<ReadonlySet<PreferenceField>>(new Set());
  const markSaving = (field: PreferenceField, on: boolean) =>
    setSaving((now) => {
      const next = new Set(now);
      if (on) next.add(field);
      else next.delete(field);
      return next;
    });
  const toast = useToast();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [timersOpen, setTimersOpen] = useState(false);
  const [draftReading, setDraftReading] = useState(formatTimer(timers.readingSeconds));
  const [draftSimulation, setDraftSimulation] = useState(formatTimer(timers.simulationSeconds));

  const draftReadingSeconds = parseTimer(draftReading);
  const draftSimulationSeconds = parseTimer(draftSimulation);

  /** Save one switch. The new value shows at once; a refusal puts back the value it had before. */
  const save = async (field: PreferenceField, value: boolean, nextTimers?: PracticeTimers): Promise<boolean> => {
    const previous = prefs[field];
    markSaving(field, true);
    setPref(field, value);
    try {
      await updateMe(preferencePatch(field, value, nextTimers));
      return true;
    } catch {
      setPref(field, previous);
      toast.error("Your change was not saved. Try again");
      return false;
    } finally {
      markSaving(field, false);
    }
  };

  const openTimers = () => {
    setDraftReading(formatTimer(timers.readingSeconds));
    setDraftSimulation(formatTimer(timers.simulationSeconds));
    setTimersOpen(true);
  };

  /** Turning the switch on only counts once the timers are confirmed and saved; closing the modal leaves it as it was. */
  const confirmTimers = async () => {
    if (draftReadingSeconds === null || draftSimulationSeconds === null) return;
    const next = { readingSeconds: draftReadingSeconds, simulationSeconds: draftSimulationSeconds };
    if (await save("needs_extra_time", true, next)) {
      setTimers(next);
      setTimersOpen(false);
    }
  };

  const closeOnboarding = () => {
    if (examCode && session?.user.id) rememberOnboardingSeen(examCode, session.user.id);
    setShowOnboarding(false);
  };

  return (
    <>
      <div className="space-y-6">
        <Panel title="Preferences" description="Accessibility, AI consent and notifications. Athena adapts to your past sessions.">
          <SettingsRows className="rounded-none border-0">
            <SettingsRow
              icon={HiOutlineSparkles}
              title="AI training consent"
              meta="Allow OSCE Guide to use anonymised transcripts of your practice consultations to improve the AI patients and the feedback they give. Your name and email are never included, and you can turn this off at any time"
              trailing={
                <Switch
                  checked={prefs.ai_training_consent}
                  disabled={saving.has("ai_training_consent")}
                  onChange={(next) => void save("ai_training_consent", next)}
                  label="AI training consent"
                />
              }
            />
            <SettingsRow
              icon={HiOutlineClock}
              title="Extra reading time"
              meta={
                prefs.needs_extra_time
                  ? `Your timers: ${describeTimer(timers.readingSeconds)} reading, ${describeTimer(timers.simulationSeconds)} consultation`
                  : "Give yourself longer than the exam allows to read the doctor information and to consult. Your own timers replace the exam's in practice stations"
              }
              trailing={
                <span className="flex items-center gap-3">
                  {prefs.needs_extra_time ? (
                    <Button variant="secondary" size="sm" onClick={() => openTimers()}>
                      Edit
                    </Button>
                  ) : null}
                  <Switch
                    checked={prefs.needs_extra_time}
                    disabled={saving.has("needs_extra_time")}
                    onChange={(next) => (next ? openTimers() : void save("needs_extra_time", false))}
                    label="Extra reading time"
                  />
                </span>
              }
            />
            {offersWaitingEmail ? (
              <SettingsRow
                icon={HiOutlineEnvelope}
                title="Email me when a colleague is waiting"
                meta="Get an email when someone you invited to practise together is waiting for you in a peer session"
                trailing={
                  <Switch
                    checked={prefs.colleague_waiting_email}
                    disabled={saving.has("colleague_waiting_email")}
                    onChange={(next) => void save("colleague_waiting_email", next)}
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
        </Panel>
      </div>

      {timersOpen ? (
        <Modal width="min(95vw, 480px)" height="fit-content" title="Extra reading time" onClose={() => setTimersOpen(false)}>
          <div className="space-y-4 p-1">
            <p className="text-osce-body text-ink-muted">
              Set your own timers for practice stations. They replace the exam&apos;s default times while this is on.
            </p>
            <Input
              label="Reading timer (doctor information)"
              name="readingTimer"
              inputMode="numeric"
              placeholder="04:00"
              value={draftReading}
              onChange={(event) => setDraftReading(event.target.value)}
              error={draftReadingSeconds === null ? "Minutes and seconds, such as 04:00" : null}
            />
            <Input
              label="Simulation timer (consultation)"
              name="simulationTimer"
              inputMode="numeric"
              placeholder="14:00"
              value={draftSimulation}
              onChange={(event) => setDraftSimulation(event.target.value)}
              error={draftSimulationSeconds === null ? "Minutes and seconds, such as 14:00" : null}
            />
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setTimersOpen(false)}>
                Cancel
              </Button>
              <Button isLoading={saving.has("needs_extra_time")} onClick={() => void confirmTimers()}>
                Use these timers
              </Button>
            </div>
          </div>
        </Modal>
      ) : null}

      {showOnboarding ? (
        <Modal width="min(95vw, 560px)" height="fit-content" title="Athena onboarding" onClose={closeOnboarding} hideCloseButton>
          <OnboardingFlow onComplete={closeOnboarding} />
        </Modal>
      ) : null}
    </>
  );
}
