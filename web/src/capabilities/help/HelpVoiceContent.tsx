"use client";
import { LuMousePointer2, LuWand } from "react-icons/lu";
import { AthenaIdentity } from "@/foundation/ui";
import { helpType } from "@/foundation/ui/helpType";
import { HelpTranscriptions } from "@/foundation/livekit/HelpTranscriptions";
import { isUiGuidanceEnabled, UiGuidanceOverlay, GuidanceProgressPanel, AssistantCards } from "@/foundation/livekit/guidance";
import { useSurface } from "@/capabilities/SurfaceContext";
import { cardLinkFor } from "@/capabilities/help/refRoutes";
import { useHelpGuidance } from "./useHelpGuidance";
export function HelpVoiceContent({
  voiceHelpIntent,
  onOpenHelpArticle,
}: {
  voiceHelpIntent: "faq" | "guide";
  /** Opens a help article Athena suggested inside the dock. */
  onOpenHelpArticle: (slug: string) => void;
}) {
  const { state, screenUiGuidanceSession, isGuidanceToolRunning, navigationMode, navPromptHighlight,
    publishNavigationMode, pointerTarget, progressStep, progressLabel, cards, dismissCard, athenaDescription } = useHelpGuidance(voiceHelpIntent);
  const { hrefFor } = useSurface();
  return <>
    <div className="mb-4 flex shrink-0 flex-col items-center justify-center"><AthenaIdentity description={athenaDescription} /></div>
          {/* Tool-running loading banner */}
          {screenUiGuidanceSession &&
            isGuidanceToolRunning &&
            state !== "disconnected" && (
            <div className="flex items-center gap-2.5 mb-3 px-3 py-2 bg-osce-accent-muted border border-osce-accent-subtle rounded-lg shrink-0">
              <div className="flex gap-1 shrink-0">
                <span className="w-1.5 h-1.5 rounded-full bg-osce-accent-light animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-osce-accent-light animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-osce-accent-light animate-bounce [animation-delay:300ms]" />
              </div>
              <p className="text-osce-meta text-osce-accent">
                {navigationMode === "automate" && isUiGuidanceEnabled()
                  ? "Hands-off navigation in progress…"
                  : "Capturing and analysing your screen…"}
              </p>
            </div>
          )}

          {state !== "disconnected" && (
            <div className="mb-3 flex min-h-[160px] flex-col overflow-hidden rounded-lg border border-osce-border">
              <div className={`shrink-0 border-b border-osce-border-light bg-osce-canvas px-3 py-2 ${helpType.groupLabel}`}>
                Transcription
              </div>
              <HelpTranscriptions className="min-h-[120px] flex-1" />
            </div>
          )}

          {state !== "disconnected" && screenUiGuidanceSession && (
            <div
              className={`mb-3 shrink-0 rounded-xl border bg-white p-3.5 transition-shadow ${
                navPromptHighlight
                  ? "border-osce-accent-light shadow-md ring-2 ring-osce-accent-subtle/70"
                  : "border-osce-border"
              }`}
              role="radiogroup"
              aria-label="Navigation style"
            >
              <div className="mb-3">
                <p className={helpType.title}>
                  How should Athena navigate?
                </p>
                <p className={`mt-1 ${helpType.support}`}>
                  Choose a mode for this chat. You can change it anytime.
                </p>
              </div>

              <div className="flex flex-col gap-2">
                <button
                  type="button"
                  role="radio"
                  aria-checked={navigationMode === "guide"}
                  onClick={() => void publishNavigationMode("guide")}
                  className={`flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left outline-none transition-all focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 ${
                    navigationMode === "guide"
                      ? "border-osce-accent bg-osce-accent-muted"
                      : "border-osce-border bg-white hover:border-osce-border hover:bg-osce-canvas"
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                      navigationMode === "guide"
                        ? "bg-osce-accent-hover text-white"
                        : "bg-osce-border-light text-osce-ink-600"
                    }`}
                  >
                    <LuMousePointer2 className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className={helpType.rowTitle}>
                        Guide me
                      </span>
                      <span
                        className={`h-4 w-4 shrink-0 rounded-full border-2 ${
                          navigationMode === "guide"
                            ? "border-osce-accent-hover bg-osce-accent-hover shadow-[inset_0_0_0_2px_white]"
                            : "border-osce-border bg-white"
                        }`}
                        aria-hidden
                      />
                    </span>
                    <span className={`mt-1 block ${helpType.support}`}>
                      Athena highlights what to tap. You take each step.
                    </span>
                  </span>
                </button>

                <button
                  type="button"
                  role="radio"
                  aria-checked={navigationMode === "automate"}
                  onClick={() => void publishNavigationMode("automate")}
                  className={`flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left outline-none transition-all focus-visible:ring-2 focus-visible:ring-osce-accent focus-visible:ring-offset-2 ${
                    navigationMode === "automate"
                      ? "border-osce-accent bg-osce-accent-muted"
                      : "border-osce-border bg-white hover:border-osce-border hover:bg-osce-canvas"
                  }`}
                >
                  <span
                    className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                      navigationMode === "automate"
                        ? "bg-osce-accent-hover text-white"
                        : "bg-osce-border-light text-osce-ink-600"
                    }`}
                  >
                    <LuWand className="h-4 w-4" aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center justify-between gap-2">
                      <span className={helpType.rowTitle}>
                        Navigate for me
                      </span>
                      <span
                        className={`h-4 w-4 shrink-0 rounded-full border-2 ${
                          navigationMode === "automate"
                            ? "border-osce-accent-hover bg-osce-accent-hover shadow-[inset_0_0_0_2px_white]"
                            : "border-osce-border bg-white"
                        }`}
                        aria-hidden
                      />
                    </span>
                    <span className={`mt-1 block ${helpType.support}`}>
                      Athena clicks for you while you stay on voice.
                    </span>
                  </span>
                </button>
              </div>
            </div>
          )}
    <AssistantCards cards={cards} onDismiss={dismissCard} linkFor={(ref) => cardLinkFor(ref, { hrefFor, openHelpArticle: onOpenHelpArticle })} />
    <UiGuidanceOverlay pointerTarget={pointerTarget} /><GuidanceProgressPanel step={progressStep} label={progressLabel} />
  </>;
}
