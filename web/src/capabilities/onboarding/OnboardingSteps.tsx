"use client";

import { useState, type ReactNode } from "react";
import { HiOutlineArrowLeft, HiOutlineArrowRight } from "react-icons/hi2";
import { AthenaIdentity, Button, ModalSection, Textarea, productTokens } from "@/foundation/ui";
import type { OnboardingScene } from "@/capabilities/onboarding/api";
import { AthenaVoice } from "@/capabilities/onboarding/AthenaVoice";
import { MAX_REPLY_CHARS, meetActions, sceneReply, type FlowMode, type VoiceStatus } from "@/capabilities/onboarding/onboardingModel";

const { b2cCard, b2cCardPadding } = productTokens;

/** One of Athena's lines, with her face and a label saying what kind of line it is. */
function AthenaSays({ label, children }: { label: string; children: ReactNode }) {
  return (
    <figure className="space-y-2">
      <AthenaIdentity layout="inline" title={label} description={null} imageClassName="h-8 w-8" />
      <blockquote className="ml-11 rounded-2xl rounded-tl-sm bg-osce-accent-subtle px-4 py-3 leading-relaxed text-ink">
        {children}
      </blockquote>
    </figure>
  );
}

export function MeetAthena({
  assistantName,
  userName,
  mode,
  status,
  onTurnOnVoice,
  onContinueWithoutVoice,
  onNext,
}: {
  assistantName: string;
  userName: string;
  mode: FlowMode;
  status: VoiceStatus;
  onTurnOnVoice: () => void;
  onContinueWithoutVoice: () => void;
  onNext: () => void;
}) {
  const actions = meetActions(status, mode, assistantName);
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-6 text-center`}>
      {mode === "text" ? (
        <div className="text-left">
          <AthenaSays label={assistantName}>
            Hello{userName ? `, ${userName}` : ""}! I&apos;m {assistantName}. I give you instant feedback on how you
            communicate with patients. Let me show you how I work. It only takes a minute.
          </AthenaSays>
        </div>
      ) : (
        <>
          <AthenaIdentity
            title={assistantName}
            description={`Turn on ${assistantName}'s voice to hear her introduce herself and talk you through a short demo.`}
          />
          {status === "on" && <AthenaVoice assistantName={assistantName} />}
        </>
      )}
      {/* No microphone card here: it opened the microphone a second time while
          the session start was already asking, and on an installed iOS app the
          two requests left each other unanswered. A blocked microphone is
          reported by the alert under the steps. */}
      <div className="flex flex-col items-center gap-3">
        {actions.voiceButton && (
          <Button onClick={onTurnOnVoice} isLoading={status === "connecting"}>
            {actions.voiceButton}
          </Button>
        )}
        <Button variant={actions.voiceButton ? "secondary" : "primary"} disabled={!actions.showMeEnabled} onClick={onNext}>
          Show me how it works <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
        </Button>
        {actions.offerTextMode && (
          <Button variant="ghost" size="sm" onClick={onContinueWithoutVoice}>
            Continue without voice
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * One demo scene. With voice, the person answers out loud and Athena
 * critiques it. Without, they pick or write a reply and then read the answer
 * she would model. Keyed by scene in the caller, so a new scene starts blank.
 */
export function DemoScene({
  scene,
  assistantName,
  mode,
  isFirst,
  isLast,
  onPrevious,
  onNext,
}: {
  scene: OnboardingScene;
  assistantName: string;
  mode: FlowMode;
  isFirst: boolean;
  isLast: boolean;
  onPrevious: () => void;
  onNext: () => void;
}) {
  const [reply, setReply] = useState<string | null>(null);
  const [typed, setTyped] = useState("");
  const typedReply = sceneReply(typed);
  return (
    <div className={`${b2cCard} ${b2cCardPadding} space-y-6`}>
      <header className="space-y-1 text-center">
        <h2 className="font-semibold text-ink">See {assistantName} in action</h2>
        <p className="text-sm text-ink-muted">
          {mode === "voice"
            ? `Answer ${assistantName}'s question out loud, and she will give you instant feedback.`
            : `Choose a reply or write your own, then see the answer ${assistantName} would give.`}
        </p>
      </header>
      {mode === "voice" && <AthenaVoice assistantName={assistantName} />}
      <ModalSection title="Patient">
        <p className="leading-relaxed text-ink">{scene.patientLine}</p>
      </ModalSection>
      <AthenaSays label={`${assistantName} asks:`}>{scene.question}</AthenaSays>

      {mode === "text" && reply === null && (
        <div className="space-y-4">
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium text-ink">Pick a reply</legend>
            {scene.replies.map((option) => (
              <Button
                key={option}
                variant="outline"
                className="h-auto w-full justify-start whitespace-normal py-2 text-left"
                onClick={() => setReply(option)}
              >
                {option}
              </Button>
            ))}
          </fieldset>
          <form
            className="space-y-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (typedReply) setReply(typedReply);
            }}
          >
            <Textarea
              label="Or write your own"
              rows={2}
              maxLength={MAX_REPLY_CHARS}
              value={typed}
              onChange={(event) => setTyped(event.target.value)}
            />
            <Button type="submit" variant="secondary" size="sm" disabled={!typedReply}>
              Send reply
            </Button>
          </form>
        </div>
      )}

      {mode === "text" && reply !== null && (
        <div className="space-y-4">
          <figure className="ml-auto max-w-[85%] space-y-1 text-right">
            <figcaption className="text-sm font-medium text-ink-muted">You said</figcaption>
            <blockquote className="rounded-2xl rounded-tr-sm bg-surface-raised px-4 py-3 text-left leading-relaxed text-ink">
              {reply}
            </blockquote>
          </figure>
          <AthenaSays label={`${assistantName} would say:`}>{scene.modelAnswer}</AthenaSays>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <Button variant="secondary" onClick={onPrevious} disabled={isFirst}>
          <HiOutlineArrowLeft className="h-3 w-3" aria-hidden /> Previous
        </Button>
        <Button onClick={onNext} disabled={mode === "text" && reply === null}>
          {isLast ? "Finish demo" : "Next"} <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
