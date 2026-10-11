"use client";

import { useState, type ReactNode } from "react";
import { HiOutlineArrowLeft, HiOutlineArrowRight } from "react-icons/hi2";
import { AthenaIdentity, Button, ModalBody, ModalLead, ModalSection, Textarea, type ModalTone } from "@/foundation/ui";
import type { OnboardingScene } from "@/capabilities/onboarding/api";
import { AthenaVoice } from "@/capabilities/onboarding/AthenaVoice";
import { MAX_REPLY_CHARS, meetActions, sceneReply, type FlowMode, type VoiceStatus } from "@/capabilities/onboarding/onboardingModel";

/** Section title type, so a legend reads like every ModalSection title beside it. */
const SECTION_TITLE = "text-osce-meta font-semibold text-osce-ink-900";

/** One line of the demo conversation, titled with who says it. */
function Line({ title, tint, children }: { title: ReactNode; tint: ModalTone; children: ReactNode }) {
  return (
    <ModalSection title={title} tint={tint}>
      <p className="leading-relaxed text-ink">{children}</p>
    </ModalSection>
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
    <ModalBody className="text-center">
      {mode === "text" ? (
        <div className="text-left">
          <Line title={assistantName} tint="violet">
            Hello{userName ? `, ${userName}` : ""}! I&apos;m {assistantName}. I give you instant feedback on how you
            communicate with patients. Let me show you how I work. It only takes a minute.
          </Line>
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
        {actions.offerTextMode && (
          <Button variant="secondary" onClick={onContinueWithoutVoice}>
            Continue without voice
          </Button>
        )}
        {actions.hint && <p className="text-osce-meta text-ink-muted">{actions.hint}</p>}
        {actions.showMe && (
          <Button onClick={onNext}>
            Show me how it works <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
          </Button>
        )}
      </div>
    </ModalBody>
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
    <ModalBody>
      <ModalLead
        title={`See ${assistantName} in action`}
        description={
          mode === "voice"
            ? `Answer ${assistantName}'s question out loud, and she will give you instant feedback.`
            : `Choose a reply or write your own, then see the answer ${assistantName} would give.`
        }
      />
      {mode === "voice" && <AthenaVoice assistantName={assistantName} />}
      <Line title="Patient" tint="muted">
        {scene.patientLine}
      </Line>
      <Line title={assistantName} tint="violet">
        {scene.question}
      </Line>

      {mode === "text" && reply === null && (
        <div>
          <fieldset className="space-y-3 pb-6">
              <legend className={`mb-2.5 ${SECTION_TITLE}`}>Pick a reply</legend>
              {scene.replies.map((option) => (
                <Button
                  key={option}
                  variant="outline"
                  fullWidth
                  className="h-auto justify-start whitespace-normal py-3 text-left"
                  onClick={() => setReply(option)}
                >
                  {option}
                </Button>
              ))}
          </fieldset>
          <form
            className="mt-6 space-y-2.5"
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
        <>
          <Line title="You" tint="muted">
            {reply}
          </Line>
          <Line
            title={
              <>
                {assistantName} <span className="font-normal text-ink-muted">· What you could have said</span>
              </>
            }
            tint="violet"
          >
            {scene.modelAnswer}
          </Line>
        </>
      )}

      <div className="flex items-center justify-between gap-3">
        <Button variant="secondary" onClick={onPrevious} disabled={isFirst}>
          <HiOutlineArrowLeft className="h-3 w-3" aria-hidden /> Previous
        </Button>
        <Button onClick={onNext} disabled={mode === "text" && reply === null}>
          {isLast ? "Finish demo" : "Next"} <HiOutlineArrowRight className="h-3 w-3" aria-hidden />
        </Button>
      </div>
    </ModalBody>
  );
}
