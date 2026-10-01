"use client";
import { useEffect, useRef, useState } from "react";
import { useMaybeRoomContext } from "@livekit/components-react";
import { RoomEvent, type Participant, type TranscriptionSegment } from "livekit-client";
import { helpType } from "@/foundation/ui/helpType";

interface StoredTranscription {
  segment: TranscriptionSegment;
  participantIdentity: string | undefined;
}

// Transcriptions component with fixed height and internal scroll
export function HelpTranscriptions({ className }: { className?: string }) {
  const room = useMaybeRoomContext();
  const [transcriptions, setTranscriptions] = useState<{
    [id: string]: StoredTranscription;
  }>({});
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!room) return;
    const updateTranscriptions = (
      segments: TranscriptionSegment[],
      participant?: Participant,
    ) => {
      setTranscriptions((prev) => {
        const newTranscriptions = { ...prev };
        for (const segment of segments) {
          newTranscriptions[segment.id] = {
            segment,
            participantIdentity: participant?.identity,
          };
        }
        return newTranscriptions;
      });
    };
    room.on(RoomEvent.TranscriptionReceived, updateTranscriptions);
    return () => {
      room.off(RoomEvent.TranscriptionReceived, updateTranscriptions);
    };
  }, [room]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop =
        scrollContainerRef.current.scrollHeight;
    }
  }, [transcriptions]);

  return (
    <div
      ref={scrollContainerRef}
      className={`${className} overflow-y-auto overflow-x-hidden p-2`}
    >
      {Object.values(transcriptions).length > 0 ? (
        <div className="flex flex-col pt-1 overflow-hidden">
          {Object.values(transcriptions)
            .sort(
              (a, b) =>
                a.segment.firstReceivedTime - b.segment.firstReceivedTime,
            )
            .map((storedItem) => {
              const { segment, participantIdentity } = storedItem;
              const isUser =
                participantIdentity === room?.localParticipant.identity;

              return (
                <div
                  key={segment.id}
                  className={`mb-2 ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div className="flex items-start overflow-hidden">
                    {!isUser && (
                      <div className="mr-2 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-osce-border-light">
                        <span className="text-osce-meta font-medium text-osce-ink-500">A</span>
                      </div>
                    )}

                    <div
                      className={`w-auto max-w-[80%] rounded-lg px-2.5 py-1.5 ${helpType.prose} ${
                        isUser
                          ? "bg-osce-accent-subtle text-osce-accent-hover"
                          : "bg-osce-border-light text-osce-ink-900"
                      } overflow-hidden whitespace-pre-wrap break-words`}
                    >
                      <p>{segment.text}</p>
                      <span className="mt-0.5 block text-osce-meta text-osce-ink-500">
                        {(() => {
                          const v = segment.firstReceivedTime;
                          const d =
                            typeof v === "number"
                              ? new Date(v)
                              : new Date(String(v ?? ""));
                          return d && Number.isFinite(d.getTime())
                            ? d.toLocaleTimeString([], {
                                hour: "2-digit",
                                minute: "2-digit",
                              })
                            : "";
                        })()}
                      </span>
                    </div>

                    {isUser && (
                      <div className="ml-2 mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-osce-accent-subtle">
                        <span className="text-osce-meta font-medium text-osce-accent">Y</span>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
        </div>
      ) : (
        <div className="h-full flex items-center justify-center">
          <p className={`text-center ${helpType.support}`}>
            Transcript will appear here
          </p>
        </div>
      )}
    </div>
  );
}

