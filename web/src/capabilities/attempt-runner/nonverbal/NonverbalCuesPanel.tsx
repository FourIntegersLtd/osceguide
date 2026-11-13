"use client";

import { useEffect, useRef } from "react";
import { HiOutlineVideoCamera } from "react-icons/hi2";
import { B2CPanelCardHeader, B2CPanelCardHeaderIcon, Button, cn } from "@/foundation/ui";
import type { CueTone } from "./cues";
import { NonverbalConsent } from "./NonverbalConsent";
import { cueLabel, feedRowTime, panelKind } from "./panelState";
import type { Nonverbal } from "./useNonverbal";

const TONE_STYLES: Record<CueTone, string> = {
  success: "border-osce-success-border bg-osce-success-bg text-osce-ink-900",
  warning: "border-osce-warning-border bg-osce-warning-bg text-osce-ink-900",
  neutral: "border-osce-border bg-osce-surface text-b2c-text-muted",
};

export function TurnOff({ onClick }: { onClick: () => void }) {
  return <button type="button" onClick={onClick} className="self-start text-osce-meta text-b2c-text-muted underline focus:outline-none focus:ring-2 focus:ring-osce-accent">Turn off</button>;
}

const note = "text-osce-meta leading-relaxed text-b2c-text-muted";

function SelfView({ stream }: { stream: MediaStream | null }) {
  const ref = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream;
  }, [stream]);
  if (!stream) return null;
  return <video ref={ref} muted playsInline autoPlay aria-label="Your camera" className="w-24 -scale-x-100 rounded-osce-md border border-osce-border" />;
}

/**
 * Live non-verbal cues: the current state, then what just happened, each under the exam's own
 * label. Describes behaviour only, never feelings, and has no red: these are cues, not grades.
 */
export function NonverbalCuesPanel({ nonverbal, isLive }: { nonverbal: Nonverbal; isLive: boolean }) {
  const { read, off, capture, live, events, turnOn, turnOff } = nonverbal;
  if (!read) return null;
  const kind = panelKind({ supported: read.supported, consented: read.consented, off, isLive, status: capture.status });
  if (kind === "hidden") return null;
  const started = capture.startedAtMs ?? 0;

  return <div className="flex min-h-[240px] flex-1 flex-col overflow-hidden lg:min-h-0">
    <B2CPanelCardHeader>
      <span className="flex min-w-0 items-center gap-2.5">
        <B2CPanelCardHeaderIcon icon={HiOutlineVideoCamera} tone="emerald" />
        {read.lingo.heading}
      </span>
    </B2CPanelCardHeader>
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-3">
      {kind === "invite" && <>
        <p className={note}>Get live cues on eye line, nodding and expression. Your video stays on this device.</p>
        <div><Button type="button" variant="secondary" onClick={turnOn}>Turn on</Button></div>
      </>}
      {kind === "denied" && <p role="status" className={note}>Camera access is blocked. Allow it in your browser to get non-verbal cues. Your consultation is not affected.</p>}
      {kind === "unavailable" && <p role="status" className={note}>Non-verbal cues could not start on this device. Your consultation is not affected.</p>}
      {kind === "ready" && <>
        <p className={note}>Camera ready. Cues start with the consultation.</p>
        <TurnOff onClick={turnOff} />
      </>}
      {kind === "live" && <>
        <div className="flex items-start gap-3">
          <SelfView stream={capture.stream} />
          <p className={cn("rounded-osce-md border px-3 py-2 text-osce-data font-medium", TONE_STYLES[live.tone])}>{live.text}</p>
        </div>
        <ul aria-live="polite" aria-relevant="additions" className="flex flex-col gap-2">
          {events.map((event) => (
            <li key={`${event.at_ms}-${event.text}`} className="rounded-osce-md border border-osce-border bg-osce-surface px-3 py-2">
              <span className="flex items-baseline justify-between gap-2 text-osce-caption text-b2c-text-muted">
                <span>{cueLabel(event.kind, read.lingo)}</span>
                <span className="tabular-nums">{feedRowTime(event.at_ms, started)}</span>
              </span>
              <span className="block text-osce-data font-medium text-osce-ink-900">{event.text}</span>
            </li>
          ))}
        </ul>
        <TurnOff onClick={turnOff} />
        <p className="text-osce-caption leading-snug text-b2c-text-muted">A guide while you practise, not your mark.</p>
      </>}
    </div>
    <NonverbalConsent isOpen={nonverbal.consentOpen} version={read.consent_version} onCancel={nonverbal.closeConsent} onGranted={nonverbal.granted} onStale={nonverbal.reload} />
  </div>;
}
