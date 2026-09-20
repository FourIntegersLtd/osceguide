"use client";

import { BarVisualizer, useConnectionState, useVoiceAssistant } from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import { HiOutlinePhoneXMark } from "react-icons/hi2";
import { AthenaIdentity, Button, cn, productTokens } from "@/foundation/ui";

export function DebriefVoiceStage({ onEnd }: { onEnd: () => void }) {
  const { state, audioTrack } = useVoiceAssistant();
  const connection = useConnectionState();
  const connecting = connection !== ConnectionState.Connected;
  return (
    <>
      <AthenaIdentity title="Athena Moderator" description="Speak naturally to discuss your performance" className="mb-5" />
      <div className="mb-6 w-full overflow-hidden rounded-osce-lg border border-osce-accent-subtle bg-osce-accent-muted px-4 py-4">
        <BarVisualizer state={state} barCount={5} trackRef={audioTrack}
          style={{ height: "64px", opacity: state === "disconnected" ? 0.5 : 1 }} />
        {state !== "disconnected" && <p role="status" className="mt-1.5 text-center text-osce-body font-medium capitalize text-b2c-text-muted">{state}</p>}
      </div>
      {connecting ? <Button fullWidth disabled isLoading>Connecting...</Button> : (
        <button type="button" className={cn(productTokens.b2cLivekitEndButton, "w-full gap-2")} onClick={onEnd}>
          <HiOutlinePhoneXMark className="h-4 w-4" aria-hidden /><span>End debrief session</span>
        </button>
      )}
    </>
  );
}
