"use client";

import { useEffect, useMemo, useState } from "react";
import { HiOutlineArrowRight } from "react-icons/hi2";
import { Alert, AthenaIdentity, Button, LoadingSpinner, ModalBody, cn } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { VoiceRoom } from "@/foundation/livekit";
import { useOnboardingVoice } from "@/capabilities/onboarding/useOnboardingVoice";
import { DemoScene, MeetAthena } from "@/capabilities/onboarding/OnboardingSteps";
import { offersSkipTour, onboardingPosition, voiceErrorCopy, type FlowMode, type Step } from "@/capabilities/onboarding/onboardingModel";

const STEPS: { id: Step; label: string }[] = [
  { id: "meet", label: "Meet Athena" },
  { id: "demo", label: "Watch a demo consultation" },
  { id: "invitation", label: "Your first station" },
];

/**
 * Athena's introduction, and one consultation shown rather than described.
 *
 * Three steps: she introduces herself, the person answers a patient and hears
 * (or reads) what she makes of it, and then they are invited to start their
 * own. Voice comes first: the demo waits until Athena can be heard, unless the
 * person chooses "Continue without voice", which turns the walkthrough into
 * reading. One voice session spans the steps — see `useOnboardingVoice` — so
 * moving between scenes is an announcement, not a reconnection.
 *
 * `onComplete` is the caller's: a dashboard that opened this in a modal closes
 * it and remembers, and a settings page replaying it stays put. "Skip tour" on
 * the introduction and the demo calls `onSkip` (default `onComplete`), so a
 * host can close in place on skip and navigate only on completion. This
 * component does not navigate, because where "start practising" goes is the
 * surface's business and a capability may not know the arm it is mounted on.
 */
export function OnboardingFlow({ onComplete, onSkip = onComplete }: { onComplete: () => void; onSkip?: () => void }) {
  const voice = useOnboardingVoice();
  const { session } = useSession();
  const [step, setStep] = useState<Step>("meet");
  const [mode, setMode] = useState<FlowMode>("voice");
  const [sceneIndex, setSceneIndex] = useState(0);
  const scene = voice.scenes[sceneIndex];
  const position = useMemo(() => onboardingPosition(step, sceneIndex), [step, sceneIndex]);
  const { announce, status } = voice;

  // Voice starts on a press, never on mount: each start opens a billed voice
  // session and asks for the microphone, and opening this screen (or having
  // it opened for you on the dashboard) is not asking to hear Athena.
  const startVoice = () => void voice.start(position);

  // Also re-run when the room comes up, so a step changed while it was
  // connecting is announced then; the session opened on the step it started on.
  useEffect(() => {
    if (mode !== "voice" || status !== "on" || (position.phase === "demo" && !scene)) return;
    announce(position);
  }, [mode, status, position, scene, announce]);

  const continueWithoutVoice = () => {
    voice.leave();
    setMode("text");
  };

  const finish = () => {
    voice.leave();
    onComplete();
  };

  const skip = () => {
    voice.leave();
    onSkip();
  };

  return (
    <VoiceRoom
      className="mx-auto w-full max-w-xl space-y-7"
      grant={step === "invitation" || mode === "text" ? null : voice.grant}
      onConnected={voice.onConnected}
      onDisconnected={voice.onDisconnected}
    >
      <div className="flex items-center justify-between gap-3">
        <ol className="flex items-center" aria-label="Onboarding steps">
          {STEPS.map((entry, index) => (
            <li
              key={entry.id}
              aria-current={entry.id === step ? "step" : undefined}
              title={entry.label}
              className={cn(
                "border-l border-osce-border px-4 font-mono text-osce-body tabular-nums first:border-l-0 first:pl-0",
                entry.id === step ? "font-semibold text-osce-ink-900" : "text-b2c-text-muted",
              )}
            >
              {String(index + 1).padStart(2, "0")}
              <span className="sr-only"> {entry.label}</span>
            </li>
          ))}
        </ol>
        {offersSkipTour(step) && (
          <Button variant="ghost" size="sm" onClick={skip}>
            Skip tour
          </Button>
        )}
      </div>

      {step === "meet" && (
        <MeetAthena
          assistantName={voice.assistantName}
          userName={session?.user.name ?? ""}
          mode={mode}
          status={status}
          onTurnOnVoice={startVoice}
          onContinueWithoutVoice={continueWithoutVoice}
          onNext={() => setStep("demo")}
        />
      )}

      {/* Voice that dropped mid-demo; reaching the demo in voice mode needed it on. */}
      {step === "demo" && mode === "voice" && status === "off" && !voice.error && (
        <div className="flex justify-center">
          <Button variant="secondary" onClick={startVoice}>
            Turn on {voice.assistantName}&apos;s voice
          </Button>
        </div>
      )}

      {step === "demo" && voice.loadingScenes && (
        <div className="space-y-2.5 text-center">
          <LoadingSpinner />
          <p className="text-osce-meta text-ink-muted">Loading the demo…</p>
        </div>
      )}

      {step === "demo" && !voice.loadingScenes && !scene && (
        <ModalBody className="text-center">
          <p className="text-osce-meta text-ink-muted">
            {voice.scenesError
              ? "We couldn't load the demo right now. Please try again."
              : "The demo is not available for your exam yet."}
          </p>
          <Button onClick={() => setStep("invitation")}>
            Skip the demo <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
          </Button>
        </ModalBody>
      )}

      {step === "demo" && scene && (
        <DemoScene
          key={sceneIndex}
          scene={scene}
          assistantName={voice.assistantName}
          mode={mode}
          isFirst={sceneIndex === 0}
          isLast={sceneIndex === voice.scenes.length - 1}
          onPrevious={() => setSceneIndex((index) => Math.max(0, index - 1))}
          onNext={() => {
            if (sceneIndex < voice.scenes.length - 1) setSceneIndex((index) => index + 1);
            else setStep("invitation");
          }}
        />
      )}

      {step === "invitation" && (
        <ModalBody className="text-center">
          <AthenaIdentity
            title={voice.assistantName}
            description="You've seen how Athena analyzes a consultation. Ready to start practicing and get your own personalized feedback?"
          />
          <Button onClick={finish}>Start my first consultation</Button>
        </ModalBody>
      )}

      {voice.error && mode === "voice" && (
        <Alert tone="warning">
          <div className="space-y-2.5">
            <p>{voiceErrorCopy(errorMessage(voice.error), voice.assistantName)}</p>
            <Button size="sm" variant="secondary" onClick={startVoice}>
              Try voice again
            </Button>
          </div>
        </Alert>
      )}
      {voice.mic.message && <Alert tone="warning">{voice.mic.message}</Alert>}
    </VoiceRoom>
  );
}
