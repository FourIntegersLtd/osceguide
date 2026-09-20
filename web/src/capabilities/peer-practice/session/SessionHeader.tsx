"use client";

import { Button } from "@/foundation/ui";
import type { RunnerPhase } from "../support/sessionState";
import { SafetyActions } from "./SafetyActions";
const titles: Partial<Record<RunnerPhase, string>> = { preparation: "Preparation Phase", consultation: "Live Consultation", debrief: "Debrief", waiting_partner: "Waiting for your partner…" };
const labels: Partial<Record<RunnerPhase, string>> = { preparation: "Reading", consultation: "Simulation", debrief: "Debrief" };
export function SessionHeader({ role, phase, countdown, onEndSession, busy, sessionId }: {
  role: string; phase: RunnerPhase; countdown: string | null; onEndSession: () => void; busy: boolean; sessionId: string;
}) {
  return <header className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-surface p-4">
    <div><h1 className="font-semibold">{titles[phase] ?? "Practice session"}</h1><p className="text-ink-muted">Role: <span className="font-medium capitalize text-accent">{role}</span></p></div>
    <div className="flex flex-wrap items-center gap-3">
      <div className="text-center"><p role="timer" className="font-mono text-xl font-bold">{countdown ?? "—"}</p><p className="text-sm text-ink-muted">{labels[phase] ?? "Waiting"}</p></div>
      {(phase === "consultation" || phase === "debrief") && <SafetyActions sessionId={sessionId} />}
      <Button variant="danger" onClick={onEndSession} disabled={busy}>End session</Button>
    </div>
  </header>;
}
