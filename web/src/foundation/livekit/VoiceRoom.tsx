"use client";

import "@livekit/components-styles";
import { useCallback, useRef } from "react";
import type { ReactNode } from "react";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import { DisconnectReason, type Room } from "livekit-client";
import type { RoomGrant } from "@/foundation/livekit/types";

export interface VoiceRoomProps {
  grant: RoomGrant | null;
  children: ReactNode;
  /** Called once the room is up. */
  onConnected?: (room: Room) => void;
  /** `unexpected` is true for a drop the person did not ask for. */
  onDisconnected?: (unexpected: boolean) => void;
  onError?: (error: Error) => void;
  /** Publish the microphone. False for an observer. */
  audio?: boolean;
}

/**
 * A connected room, and nothing else.
 *
 * Every voice surface — a consultation, a help session, a supervisor observing
 * a circuit — connects through this one component, so reconnection, audio
 * rendering and the difference between hanging up and dropping out are decided
 * once. The old client had four copies of this and they disagreed about all
 * three.
 */
export function VoiceRoom({
  grant,
  children,
  onConnected,
  onDisconnected,
  onError,
  audio = true,
}: VoiceRoomProps) {
  const roomRef = useRef<Room | null>(null);

  const handleDisconnected = useCallback(
    (reason?: DisconnectReason) => {
      // Ending the session, or tearing the room down on unmount, reports
      // CLIENT_INITIATED. Warning about those trains people to ignore the
      // warning that matters.
      const unexpected =
        reason !== undefined &&
        reason !== DisconnectReason.CLIENT_INITIATED &&
        reason !== DisconnectReason.ROOM_DELETED;
      onDisconnected?.(unexpected);
    },
    [onDisconnected],
  );

  return (
    <LiveKitRoom
      token={grant?.token}
      serverUrl={grant?.server_url}
      connect={Boolean(grant)}
      audio={audio}
      video={false}
      onConnected={() => {
        if (roomRef.current) onConnected?.(roomRef.current);
      }}
      onDisconnected={handleDisconnected}
      onError={(error) => onError?.(error)}
      // The ref gives callers the room for data messages without a context read.
      ref={(node: unknown) => {
        roomRef.current = (node as { room?: Room } | null)?.room ?? null;
      }}
    >
      <RoomAudioRenderer />
      {children}
    </LiveKitRoom>
  );
}

/**
 * Send a structured message to the agent.
 *
 * Reliable by default: the exam clock's wind-down cue is not worth dropping,
 * and the volume is a handful of packets per session.
 */
export async function publishToAgent(
  room: Room | null,
  topic: string,
  payload: Record<string, unknown>,
): Promise<void> {
  if (!room || room.state !== "connected") return;
  try {
    await room.localParticipant.publishData(
      new TextEncoder().encode(JSON.stringify({ type: topic, ...payload })),
      { reliable: true, topic },
    );
  } catch {
    // A dropped cue costs the agent its warning; the hard stop is server-side
    // and still happens, so this is not worth failing the session for.
  }
}
