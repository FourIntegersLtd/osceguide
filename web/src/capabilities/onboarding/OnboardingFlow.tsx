"use client";

import { useEffect, useRef, useState } from "react";
import { HiOutlineArrowLeft, HiOutlineArrowRight } from "react-icons/hi2";
import { Alert, AthenaIdentity, Button, LoadingSpinner, ModalSection, cn, productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { BarVisualizer, useVoiceAssistant } from "@livekit/components-react";
import { VoiceRoom, agentStateLabel } from "@/foundation/livekit";
import type { OnboardingScene } from "@/capabilities/onboarding/api";
import { useOnboardingVoice } from "@/capabilities/onboarding/useOnboardingVoice";

const { b2cCard, b2cCardPadding } = productTokens;

type Step = "meet" | "demo" | "invitation";

const STEPS: { id: Step; label: string }[] = [
  { id: "meet", label: "Meet Athena" },
  { id: "demo", label: "Watch a demo consultation" },
  { id: "invitation", label: "Your first station" },
];

/**
 * Athena's introduction, and one consultation shown rather than described.
 *
 * Three steps: she introduces herself, the person answers a patient out loud
 * and hears what she makes of it, and then they are invited to start their
 * own. One voice session spans all three — see `useOnboardingVoice` — so
 * moving between scenes is an announcement, not a reconnection.
 *
 * `onComplete` is the caller's: a dashboard that opened this in a modal closes
 * it and remembers, and a settings page replaying it stays put. This component
 * does not navigate, because where "start practising" goes is the surface's
 * business and a capability may not know the arm it is mounted on.
 */
export function OnboardingFlow({ onComplete }: { onComplete: () => void }) {
  const voice = useOnboardingVoice();
  const { session } = useSession();
  const [step, setStep] = useState<Step>("meet");
  const [sceneIndex, setSceneIndex] = useState(0);
  const scene: OnboardingScene | undefined = voice.scenes[sceneIndex];

  const { start, announce } = voice;
  // Once per visit. `start` changes identity when the microphone status does,
  // and each call opens a billed voice session; retrying is the button's job.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    void start();
  }, [start]);

  useEffect(() => {
    if (step !== "demo" || !scene) return;
    announce("demo", scene);
  }, [step, scene, announce]);

  const finish = () => {
    voice.leave();
    onComplete();
  };

  return (
    <VoiceRoom
      className="mx-auto w-full max-w-xl space-y-8"
      grant={step === "invitation" ? null : voice.grant}
      onConnected={voice.onConnected}
    >
      <ol className="flex items-center justify-center" aria-label="Onboarding steps">
        {STEPS.map((entry, index) => (
          <li
            key={entry.id}
            aria-current={entry.id === step ? "step" : undefined}
            title={entry.label}
            className={cn(
              "border-l border-osce-border px-6 font-mono text-osce-body tabular-nums first:border-l-0",
              entry.id === step ? "font-semibold text-osce-ink-900" : "text-b2c-text-muted",
            )}
          >
            {String(index + 1).padStart(2, "0")}
            <span className="sr-only"> {entry.label}</span>
          </li>
        ))}
      </ol>
      {step === "meet" && (
        <MeetAthena
          assistantName={voice.assistantName}
          userName={session?.user.name ?? ""}
          connecting={voice.starting}
          onNext={() => setStep("demo")}
        />
      )}

      {step === "demo" && voice.loadingScenes && (
        <div className={`${b2cCard} ${b2cCardPadding} text-center`}>
          <LoadingSpinner />
          <p className="mt-3 text-sm text-ink-muted">Loading the demo…</p>
        </div>
      )}

      {step === "demo" && !voice.loadingScenes && !scene && (
        <div className={`${b2cCard} ${b2cCardPadding} space-y-4 text-center`}>
          <p className="text-sm text-ink-muted">
            {voice.scenesError
              ? "We couldn't load the demo right now. Please try again."
              : "The demo is not available for your exam yet."}
          </p>
          <Button onClick={() => setStep("invitation")}>
            Skip the demo <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
          </Button>
        </div>
      )}

      {step === "demo" && scene && (
        <InteractiveDemo
          scene={scene}
          assistantName={voice.assistantName}
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
        <div className={`${b2cCard} ${b2cCardPadding} space-y-6 text-center`}>
          <AthenaIdentity
            title={voice.assistantName}
            description="You've seen how Athena analyzes a consultation. Ready to start practicing and get your own personalized feedback?"
          />
          <Button onClick={finish}>Start my first consultation</Button>
        </div>
      )}

      {voice.error && (
        <Alert tone="warning">
          {errorMessage(voice.error)} You can still read through the demo, but {voice.assistantName} will not speak.{" "}
          <Button size="sm" variant="secondary" onClick={() => voice.start()}>
            Try voice again
          </Button>
        </Alert>
      )}
      {voice.mic.message && <Alert tone="warning">{voice.mic.message}</Alert>}
    </VoiceRoom>
  );
}

/** Athena's voice as bars. The state is read out, not printed. */
function AthenaVoice({ assistantName }: { assistantName: string }) {
  const { state, audioTrack } = useVoiceAssistant();
  return (
    <div className="flex justify-center py-2">
      {/* LiveKit's stylesheet sizes the visualiser to its parent, so the box is the parent's. */}
      <div className="h-12 w-40">
        <BarVisualizer
          state={state}
          barCount={7}
          trackRef={audioTrack}
          className="[--lk-fg:rgb(var(--color-accent))] [--lk-va-bar-bg:rgb(var(--color-ink)/0.2)] [--lk-va-bar-gap:8px] [--lk-va-bar-width:6px]"
          options={{ minHeight: 16 }}
        />
      </div>
      <p aria-live="polite" className="sr-only">
        {agentStateLabel(state, assistantName)}
      </p>
    </div>
  );
}

function MeetAthena({
  assistantName,
  userName,
  connecting,
  onNext,
}: {
  assistantName: string;
  userName: string;
  connecting: boolean;
  onNext: () => void;
}) {
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-6 text-center`}>
      <AthenaIdentity
        title={assistantName}
        description={`Listen to ${assistantName} introduce herself${userName ? `, ${userName}` : ""}, then continue when you are ready.`}
      />
      <AthenaVoice assistantName={assistantName} />
      {/* No microphone card here: it opened the microphone a second time while
          the session start was already asking, and on an installed iOS app the
          two requests left each other unanswered. A blocked microphone is
          reported by the alert under the steps. */}
      <Button onClick={onNext} isLoading={connecting}>
        Show me how it works <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
      </Button>
    </div>
  );
}

function InteractiveDemo({
  scene,
  assistantName,
  isFirst,
  isLast,
  onPrevious,
  onNext,
}: {
  scene: OnboardingScene;
  assistantName: string;
  isFirst: boolean;
  isLast: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-6`}>
      <header className="space-y-1 text-center">
        <h2 className="font-semibold text-ink">See Athena in action</h2>
        <p className="text-sm text-ink-muted">
          Respond to the patient out loud, and Athena will give instant feedback.
        </p>
      </header>
      <AthenaVoice assistantName={assistantName} />
      <ModalSection title="Patient">
        <p className="leading-relaxed text-ink">{scene.patientLine}</p>
      </ModalSection>
      <p className="font-medium leading-relaxed text-accent">{scene.question}</p>
      <div className="flex items-center justify-between gap-3">
        <Button variant="secondary" onClick={onPrevious} disabled={isFirst}>
          <HiOutlineArrowLeft className="h-3 w-3" aria-hidden /> Previous
        </Button>
        <Button onClick={onNext}>
          {isLast ? "Finish demo" : "Next"} <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
