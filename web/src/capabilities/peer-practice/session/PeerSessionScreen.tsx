"use client";

import { useState } from "react";
import { Alert, B2CErrorState, Button, ConfirmModal, LoadingSpinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { VoiceRoom } from "@/foundation/livekit";
import { PeerVideoPanel } from "@/foundation/livekit/PeerVideoPanel";
import { usePeerSession } from "../support/usePeerSession";
import { SessionHeader } from "./SessionHeader";
import { PreparationPanel } from "./PreparationPanel";
import { SafetyActions } from "./SafetyActions";
import { PhaseModals } from "./modals";
import { SessionFeedback } from "./SessionFeedback";

export function PeerSessionScreen({ sessionId, onLeave, onRequeue }: { sessionId: string; onLeave: () => void; onRequeue?: (examCode: string) => void }) {
  const state = usePeerSession(sessionId);
  const [confirmingEnd, setConfirmingEnd] = useState(false);
  const [callError, setCallError] = useState<string | null>(null);
  if (state.runnerPhase === "loading" && !state.loadError) return <LoadingSpinner />;
  if (state.loadError || !state.session) return <B2CErrorState title="We couldn't load this practice session"
    description={errorMessage(state.loadError)} onRetry={state.reload}
    secondaryAction={<Button variant="secondary" onClick={onLeave}>Back to practice</Button>} />;
  const session = state.session;
  if (state.runnerPhase === "ended" || state.runnerPhase === "completed") return <SessionFeedback
    sessionId={sessionId} busy={state.busy} error={state.error} onSubmit={state.submitFeedback} onLeave={onLeave} onRequeue={onRequeue ? () => onRequeue(session.exam_code) : undefined}
    partnerEnded={!state.endedByMe && state.runnerPhase !== "completed"} />;
  const preparing = state.runnerPhase === "preparation" || state.runnerPhase === "waiting_partner";
  return <div className="flex min-h-dvh flex-col bg-canvas text-ink">
    <SessionHeader sessionId={sessionId} role={session.my_role} phase={state.runnerPhase} countdown={state.phaseCountdown}
      busy={state.busy} onEndSession={() => setConfirmingEnd(true)} />
    {state.error && <Alert tone="danger">{errorMessage(state.error)} <Button size="sm" onClick={state.reload}>Retry</Button></Alert>}
    {preparing ? (
      state.runnerPhase === "waiting_partner" ? <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col items-center justify-center gap-5 p-6 text-center">
        <h2 className="text-xl font-semibold">Waiting for your partner to join…</h2>
        <p className="text-ink-muted">The timer will start once both users have joined the session.</p>
        <SafetyActions sessionId={sessionId} noShow />
      </div> : <div className="mx-auto w-full max-w-6xl flex-1 overflow-y-auto p-4 sm:p-6">
        <PreparationPanel session={session} />
      </div>
    ) : <div className="flex min-h-0 flex-1 flex-col bg-b2c-secondary lg:flex-row lg:overflow-hidden">
      <div className="relative flex h-[38vh] min-h-[280px] w-full shrink-0 flex-col bg-b2c-secondary sm:h-[42vh] sm:min-h-[320px] lg:h-full lg:min-h-0 lg:w-3/5 lg:overflow-hidden">
        {state.dropped && <Alert tone="warning">The call dropped. Rejoin when you are ready.</Alert>}
        {callError && <Alert tone="warning">{callError}</Alert>}
        {state.grant ? <VoiceRoom className="h-full min-h-0 flex-1" grant={state.grant} video onDisconnected={state.noteDisconnected}
          onError={() => setCallError("Could not connect your camera or microphone. Check browser permissions and use the call controls to try again.")}>
          <PeerVideoPanel role={session.my_role === "patient" ? "patient" : "doctor"} />
        </VoiceRoom> : <div className="rounded-panel border border-border bg-surface p-6 text-center">
          <p className="mb-4">{state.busy ? "Connecting to your partner…" : "Your consultation is ready. Allow your microphone and camera to join."}</p>
          {state.mic.message && <Alert tone="warning">{state.mic.message}</Alert>}
          <Button disabled={state.mic.status === "insecure"} isLoading={state.busy} onClick={() => { setCallError(null); void state.connect(); }}>{state.dropped ? "Rejoin call" : "Connect camera and microphone"}</Button>
        </div>}
      </div>
      <aside className="min-h-[55vh] min-w-0 w-full flex-1 overflow-y-auto border-t border-b2c-border bg-osce-surface p-4 sm:min-h-[58vh] lg:h-full lg:min-h-0 lg:w-2/5 lg:border-l lg:border-t-0"><PreparationPanel session={session} debrief={state.runnerPhase === "debrief"} /></aside>
    </div>}
    <PhaseModals phase={state.runnerPhase} remaining={state.remaining} preparationStarted={session.preparation_started_at} />
    <ConfirmModal isOpen={confirmingEnd} onCancel={() => !state.busy && setConfirmingEnd(false)} onConfirm={async () => {
      if (await state.end("ended_by_participant")) setConfirmingEnd(false);
    }} title="End Practice Session" tone="danger" message={state.phaseCountdown ? `You have ${state.phaseCountdown} remaining in this phase. Ending the session closes the room for both of you. Are you sure?` : "Ending the session closes the room for both of you. Are you sure?"}
      confirmText="Yes, End Session" cancelText="Cancel" isLoading={state.busy} />
  </div>;
}
