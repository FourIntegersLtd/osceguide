"use client";

import { useEffect, useRef, useState } from "react";
import { HiOutlineArrowLeft, HiOutlineArrowRight } from "react-icons/hi2";
import { Alert, AthenaIdentity, Button, LoadingSpinner, ModalSection, productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { AgentTile, VoiceRoom } from "@/foundation/livekit";
import type { OnboardingScene } from "@/capabilities/onboarding/api";
import { useOnboardingVoice } from "@/capabilities/onboarding/useOnboardingVoice";

const { b2cCard, b2cCardPadding } = productTokens;

type Step = "meet" | "demo" | "invitation";

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
export function OnboardingFlow({
  onComplete,
  onSkip,
}: {
  onComplete: () => void;
  onSkip?: () => void;
}) {
  const voice = useOnboardingVoice();
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
    <div className="mx-auto w-full max-w-xl space-y-5">
      {step === "meet" && (
        <MeetAthena
          assistantName={voice.assistantName}
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
              ? "We couldn't load the demo right now."
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
        <div className={`${b2cCard} ${b2cCardPadding} space-y-4 text-center`}>
          <AthenaIdentity
            title={voice.assistantName}
            description="You have seen how a consultation is marked. Ready to have a go, and get feedback on your own?"
          />
          <Button onClick={finish}>Start my first consultation</Button>
        </div>
      )}

      {voice.error && (
        <Alert tone="warning">
          {errorMessage(voice.error)} You can still read through the demo — {voice.assistantName} just
          will not speak.{" "}
          <Button size="sm" variant="secondary" onClick={() => void voice.start()}>
            Try voice again
          </Button>
        </Alert>
      )}
      {voice.mic.message && <Alert tone="warning">{voice.mic.message}</Alert>}

      {step !== "invitation" && (
        <VoiceRoom grant={voice.grant} onConnected={voice.onConnected}>
          <AgentTile name={voice.assistantName} detail="Your AI examiner" />
        </VoiceRoom>
      )}

      {onSkip && step !== "invitation" && (
        <div className="text-center">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              voice.leave();
              onSkip();
            }}
          >
            Skip the introduction
          </Button>
        </div>
      )}
    </div>
  );
}

function MeetAthena({
  assistantName,
  connecting,
  onNext,
}: {
  assistantName: string;
  connecting: boolean;
  onNext: () => void;
}) {
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-4 text-center`}>
      <AthenaIdentity
        title={assistantName}
        description={`Listen to ${assistantName} introduce herself, then carry on when you are ready.`}
      />
      <Button onClick={onNext} isLoading={connecting}>
        Show me how it works <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
      </Button>
    </div>
  );
}

function InteractiveDemo({
  scene,
  isFirst,
  isLast,
  onPrevious,
  onNext,
}: {
  scene: OnboardingScene;
  isFirst: boolean;
  isLast: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-4`}>
      <header className="space-y-1 text-center">
        <h2 className="font-semibold text-ink">See Athena in action</h2>
        <p className="text-sm text-ink-muted">
          Answer the patient out loud, and Athena will tell you what she made of it.
        </p>
      </header>
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
