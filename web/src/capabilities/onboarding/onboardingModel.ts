/**
 * The walkthrough's decisions, kept pure so they can be tested without a room.
 *
 * Voice comes first: "Show me how it works" waits until Athena can be heard,
 * and the only way past without her is the explicit "Continue without voice",
 * which switches the walkthrough to reading (`mode: "text"`).
 */

import type { OnboardingStart } from "@/capabilities/help/api";

export type Step = "meet" | "demo" | "invitation";
export type FlowMode = "voice" | "text";
export type VoiceStatus = "off" | "connecting" | "on";

/** The longest typed reply kept; a scene's answer is a sentence or two. */
export const MAX_REPLY_CHARS = 280;

export function voiceStatus(input: { starting: boolean; granted: boolean; connected: boolean }): VoiceStatus {
  if (input.granted && input.connected) return "on";
  return input.starting || input.granted ? "connecting" : "off";
}

/**
 * Step 1's actions. The choice is the step: "Show me how it works" is not
 * shown at all until the voice is on or the person chose text, because a
 * disabled outline button looked exactly like an enabled one (C-50).
 */
export function meetActions(
  status: VoiceStatus,
  mode: FlowMode,
  assistantName: string,
): { voiceButton: string | null; showMe: boolean; offerTextMode: boolean; hint: string | null } {
  if (mode === "text" || status === "on") {
    return { voiceButton: null, showMe: true, offerTextMode: false, hint: null };
  }
  return {
    voiceButton: `Turn on ${assistantName}'s voice`,
    showMe: false,
    offerTextMode: true,
    // While connecting the voice button already says what is happening.
    hint: status === "off" ? "Pick voice or text first" : null,
  };
}

/** Skip tour is for the introduction and the demo; the last page's exit is its own button. */
export function offersSkipTour(step: Step): boolean {
  return step !== "invitation";
}

export function onboardingPosition(step: Step, sceneIndex: number): OnboardingStart {
  return step === "demo" ? { phase: "demo", scene: sceneIndex } : { phase: "intro", scene: 0 };
}

export function pauseToggle(paused: boolean, assistantName: string): { label: string; next: boolean } {
  return { label: `${paused ? "Resume" : "Pause"} ${assistantName}`, next: !paused };
}

/** Why the voice failed, then what to do. The server's reason may arrive without a full stop. */
export function voiceErrorCopy(reason: string, assistantName: string): string {
  const sentence = /[.!?]$/.test(reason.trim()) ? reason.trim() : `${reason.trim()}.`;
  return `${sentence} ${assistantName} can't speak right now. Try again, or continue without voice.`;
}

/** A typed reply as kept: trimmed and capped, or `null` when nothing was typed. */
export function sceneReply(typed: string): string | null {
  const reply = typed.trim();
  return reply ? reply.slice(0, MAX_REPLY_CHARS) : null;
}
