"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { LuCircleHelp, LuMaximize2, LuMinimize2, LuMousePointer2 } from "react-icons/lu";
import { BsInfoCircleFill } from "react-icons/bs";
import { HiOutlineChevronRight, HiPhoneXMark } from "react-icons/hi2";
import { IoMdClose } from "react-icons/io";
import { IoArrowBack } from "react-icons/io5";
import { MdMenuBook } from "react-icons/md";
import { FiPhoneCall } from "react-icons/fi";
import {
  Alert,
  AthenaIdentity,
  B2CPanelCard,
  B2CPanelCardHeader,
  Button,
  Spinner,
} from "@/foundation/ui";
import { b2cLivekitEndButton } from "@/foundation/ui/productTokens";
import { VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { HelpVoiceContent } from "./HelpVoiceContent";
import { useScreenUiGuidance, uiGuidanceIgnoreProps } from "@/foundation/livekit/guidance";
import { errorMessage } from "@/foundation/hooks";
import { useSession, useCurrentExam, helpModeChoice } from "@/foundation/session";
import { useSurface } from "@/capabilities/SurfaceContext";
import { assistantSurfaceFor } from "@/capabilities/surface";
import { KnowledgeBaseChat } from "./KnowledgeBaseChat";
import HelpArticleBrowse from "@/capabilities/help/HelpArticleBrowse";
import {
  assistantVoiceToken,
  buildClientContext,
  startAssistantSession,
} from "@/capabilities/help/api";
import type { HelpNavItem } from "@/capabilities/help/HelpPanel";

const helpHeaderIconBtn =
  "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-white/80 transition-colors hover:bg-white/10 hover:text-white sm:h-9 sm:w-9";

const helpPanelFooter =
  "shrink-0 border-t border-osce-border-light bg-white p-3 pb-[max(0.75rem,env(safe-area-inset-bottom,0px))] sm:p-4 lg:pb-4";

type HelpMode = null | "navigate" | "knowledge";

function HelpWideToggle({
  isWide,
  onToggle,
}: {
  isWide: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`${helpHeaderIconBtn} hidden lg:inline-flex`}
      aria-label={isWide ? "Shrink help panel" : "Expand help panel"}
    >
      {isWide ? (
        <LuMinimize2 className="h-4 w-4" strokeWidth={1.75} />
      ) : (
        <LuMaximize2 className="h-4 w-4" strokeWidth={1.75} />
      )}
    </button>
  );
}

function HelpChoiceScreen({
  onChooseNavigate,
  onChooseKnowledge,
  onClose,
  isWide,
  onToggleWide,
}: {
  onChooseNavigate: () => void;
  onChooseKnowledge: () => void;
  onClose: () => void;
  isWide: boolean;
  onToggleWide: () => void;
}) {
  return (
    <div className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-white text-osce-body lg:max-h-none">
      <div className="flex shrink-0 items-center justify-between bg-gradient-to-r from-osce-accent to-osce-accent-hover px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-white/20 p-1.5">
            <BsInfoCircleFill className="h-4 w-4 text-white" />
          </div>
          <span className="font-medium text-white">Need Help?</span>
        </div>
        <div className="flex items-center gap-0.5">
          <HelpWideToggle isWide={isWide} onToggle={onToggleWide} />
          <button type="button" onClick={onClose} className={helpHeaderIconBtn} aria-label="Close">
            <IoMdClose className="h-5 w-5" color="white" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">
        <AthenaIdentity className="mb-4" />
        <h3 className="text-osce-body font-semibold tracking-tight text-osce-ink-900">
          How can we help?
        </h3>
        <p className="mt-0.5 text-osce-meta text-osce-ink-500">Choose one option to get started</p>

        <B2CPanelCard className="mt-4">
          <B2CPanelCardHeader>Options</B2CPanelCardHeader>
          <ul>
            <li className="border-b border-osce-border-light">
              <button
                type="button"
                onClick={onChooseNavigate}
                className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-osce-canvas"
              >
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-osce-accent-muted text-osce-accent">
                  <LuCircleHelp className="h-4 w-4" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-osce-body font-medium text-osce-ink-900">
                    Help navigating the app
                  </span>
                  <span className="mt-0.5 block text-osce-meta leading-relaxed text-osce-ink-500">
                    Browse guides or start a voice chat with Athena
                  </span>
                </span>
                <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
              </button>
            </li>
            <li>
              <button
                type="button"
                onClick={onChooseKnowledge}
                className="flex w-full items-start gap-3 px-4 py-3.5 text-left transition hover:bg-osce-canvas"
              >
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-osce-accent-muted text-osce-accent">
                  <MdMenuBook className="h-4 w-4" aria-hidden />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-osce-body font-medium text-osce-ink-900">
                    Ask our knowledge base
                  </span>
                  <span className="mt-0.5 block text-osce-meta leading-relaxed text-osce-ink-500">
                    Questions about conditions and management
                  </span>
                </span>
                <HiOutlineChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-osce-ink-400" />
              </button>
            </li>
          </ul>
        </B2CPanelCard>
      </div>
    </div>
  );
}

function NavigateHelpPanel({
  appType,
  navItems,
  onClose,
  onBack,
  isWide,
  onToggleWide,
  launch,
  onLaunched,
}: {
  appType: string;
  navItems: HelpNavItem[];
  onClose: () => void;
  onBack: () => void;
  isWide: boolean;
  onToggleWide: () => void;
  launch: "help" | "onboarding" | null;
  onLaunched: () => void;
}) {
  const { surface } = useSurface();
  const pathname = usePathname();
  const mic = useMicPreflight();
  const screenGuidanceAvailable = useScreenUiGuidance();
  const [voiceHelpIntent, setVoiceHelpIntent] = useState<"faq" | "guide">("faq");
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const startVoice = useCallback(async (intent: "faq" | "guide" = "faq", sessionType: "help" | "onboarding" | "dashboard" = "help") => {
    setVoiceHelpIntent(intent);
    setStarting(true);
    setError(null);
    try {
      if (mic.status !== "ready" && !await mic.request()) return;
      const context = buildClientContext({
        surface: assistantSurfaceFor(surface),
        pathname,
        navItems,
      });
      const session = await startAssistantSession(sessionType, context, undefined, { voice_help_intent: intent, screen_ui_guidance: intent === "guide" && screenGuidanceAvailable });
      setGrant(await assistantVoiceToken(session.id));
    } catch (cause) {
      setGrant(null);
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setStarting(false);
    }
  }, [mic, navItems, pathname, surface, screenGuidanceAvailable]);

  useEffect(() => {
    if (!launch) return;
    onLaunched();
    void startVoice(launch === "onboarding" ? "guide" : "faq", launch === "onboarding" ? "onboarding" : "dashboard");
  }, [launch, onLaunched, startVoice]);

  const endVoice = useCallback(() => setGrant(null), []);

  const inCall = Boolean(grant);

  return (
    <div {...uiGuidanceIgnoreProps} className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-white text-osce-body shadow-lg lg:max-h-none">
      <div className="flex shrink-0 items-center justify-between bg-gradient-to-r from-osce-accent to-osce-accent-hover px-4 py-3">
        <div className="flex items-center gap-2">
          <button type="button" onClick={onBack} className={helpHeaderIconBtn} aria-label="Back">
            <IoArrowBack className="h-5 w-5" />
          </button>
          <div className="rounded-full bg-white/20 p-1.5">
            <BsInfoCircleFill className="h-4 w-4 text-white" />
          </div>
          <span className="font-medium text-white">AI Assistant</span>
        </div>
        <div className="flex items-center gap-0.5">
          <HelpWideToggle isWide={isWide} onToggle={onToggleWide} />
          <button type="button" onClick={onClose} className={helpHeaderIconBtn} aria-label="Close">
            <IoMdClose className="h-5 w-5" color="white" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">
        {error ? (
          <Alert tone="danger" className="mb-3">
            {errorMessage(error)}
          </Alert>
        ) : null}
        {mic.message ? (
          <Alert tone="warning" className="mb-3">
            {mic.message}
          </Alert>
        ) : null}

        {!inCall ? <HelpArticleBrowse appType={appType} /> : null}

        {!inCall && <div className="mb-3 hidden shrink-0 flex-col items-center justify-center lg:mt-6 lg:flex"><AthenaIdentity description="Or ask Athena by voice below" /></div>}

        {inCall ? (
          <VoiceRoom grant={grant} onDisconnected={() => endVoice()} onError={setError}>
            <HelpVoiceContent voiceHelpIntent={voiceHelpIntent} />
          </VoiceRoom>
        ) : null}
      </div>

      <div className={`${helpPanelFooter} mt-auto`}>
        {!inCall ? (
          <div className="mb-3 lg:hidden">
            <AthenaIdentity description="Or ask Athena by voice below" />
          </div>
        ) : null}
        {!inCall ? (
          <Button
            type="button"
            variant="primary"
            size="md"
            fullWidth
            onClick={() => void startVoice()}
            disabled={starting}
            className="mx-auto gap-1.5 sm:gap-2"
          >
            {starting ? (
              <div className="flex items-center justify-center gap-1.5">
                <Spinner label="Connecting" />
                <span>Connecting…</span>
              </div>
            ) : (
              <>
                <FiPhoneCall className="h-4 w-4" />
                <span>Ask a question</span>
              </>
            )}
          </Button>
        ) : (
          <button
            type="button"
            className={`${b2cLivekitEndButton} mx-auto w-full gap-1.5 sm:gap-2`}
            onClick={endVoice}
          >
            <HiPhoneXMark className="h-4 w-4" />
            <span>End conversation</span>
          </button>
        )}
        {!inCall && screenGuidanceAvailable && <Button type="button" variant="secondary" size="md" fullWidth disabled={starting} className="mt-2 gap-1.5" onClick={() => void startVoice("guide")}><LuMousePointer2 className="h-4 w-4" /><span>Guide me on screen</span></Button>}
        <div className="mt-2 px-1 text-center sm:px-2">
          <p className="text-osce-meta text-osce-ink-500">
            {inCall
              ? "If you still need further help, keep talking with Athena"
              : "Search guides above for instant answers"}
          </p>
        </div>
      </div>
    </div>
  );
}

export interface B2CHelpDockProps {
  navItems: HelpNavItem[];
  isExpanded: boolean;
  setIsExpanded: (value: boolean) => void;
  isWide: boolean;
  setIsWide: (value: boolean) => void;
  /** Help article pack; consumer defaults to the signed-in exam code. */
  appType?: string;
}

/**
 * Consumer help chrome — docked column on lg, full-screen overlay on mobile.
 * Matches the retiring client's LivekitHelpService layout and article browse.
 */
export function B2CHelpDock({
  navItems,
  isExpanded,
  setIsExpanded,
  isWide,
  setIsWide,
  appType: appTypeOverride,
}: B2CHelpDockProps) {
  const { session } = useSession();
  const { code, settings } = useCurrentExam();
  const appType = (appTypeOverride ?? code ?? "sca").toLowerCase();
  // Whether there is a choice to offer at all (`settings.help_modes`,
  // `app/core/exam_settings.py`). An exam that only lists one mode skips the
  // choice screen and opens straight into it.
  const { offersChoice: offersHelpChoice, opensDirectlyOnKnowledge } = helpModeChoice(settings);
  const [helpMode, setHelpMode] = useState<HelpMode>(null);
  const [athenaLaunch, setAthenaLaunch] = useState<"help" | "onboarding" | null>(null);

  useEffect(() => {
    const open = (event: Event) => {
      const kind = (event as CustomEvent<{ kind?: string }>).detail?.kind;
      setIsExpanded(true);
      setHelpMode("navigate");
      setAthenaLaunch(kind === "onboarding" ? "onboarding" : "help");
    };
    window.addEventListener("osce:open-athena", open);
    return () => window.removeEventListener("osce:open-athena", open);
  }, [setIsExpanded]);

  const handleClose = useCallback(() => {
    setHelpMode(null);
    setIsExpanded(false);
    setIsWide(false);
  }, [setIsExpanded, setIsWide]);

  const toggleWide = useCallback(() => setIsWide(!isWide), [isWide, setIsWide]);

  if (!session) return null;

  const panelShell = isExpanded
    ? "fixed inset-0 z-50 flex h-[100dvh] max-h-[100dvh] w-full flex-col lg:static lg:z-auto lg:h-full lg:max-h-none lg:w-auto"
    : "lg:h-full";

  if (!isExpanded) {
    return (
      <div className={panelShell}>
        <div className="fixed bottom-[calc(0.5rem+env(safe-area-inset-bottom,0px))] right-4 z-50">
          <Button
            type="button"
            variant="primary"
            size="lg"
            onClick={() => setIsExpanded(true)}
            className="h-11 w-11 px-0 lg:w-auto lg:gap-2 lg:px-4"
            aria-label="Need Help?"
          >
            <LuCircleHelp className="h-5 w-5 shrink-0" aria-hidden />
            <span className="hidden pr-0.5 font-medium lg:inline">Need Help?</span>
          </Button>
        </div>
      </div>
    );
  }

  let panel: ReactNode;
  if (helpMode === null && offersHelpChoice) {
    panel = (
      <HelpChoiceScreen
        onClose={handleClose}
        onChooseNavigate={() => setHelpMode("navigate")}
        onChooseKnowledge={() => setHelpMode("knowledge")}
        isWide={isWide}
        onToggleWide={toggleWide}
      />
    );
  } else if (helpMode === "knowledge" || (helpMode === null && opensDirectlyOnKnowledge)) {
    panel = (
      <div {...uiGuidanceIgnoreProps} className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-white text-osce-body shadow-lg lg:max-h-none">
        <div className="flex shrink-0 items-center justify-between bg-gradient-to-r from-osce-accent to-osce-accent-hover px-4 py-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setHelpMode(null)}
              className={helpHeaderIconBtn}
              aria-label="Back"
            >
              <IoArrowBack className="h-5 w-5" />
            </button>
            <div className="rounded-full bg-white/20 p-1.5">
              <MdMenuBook className="h-4 w-4 text-white" />
            </div>
            <span className="font-medium text-white">Knowledge base</span>
          </div>
          <div className="flex items-center gap-0.5">
            <HelpWideToggle isWide={isWide} onToggle={toggleWide} />
            <button type="button" onClick={handleClose} className={helpHeaderIconBtn} aria-label="Close">
              <IoMdClose className="h-5 w-5" color="white" />
            </button>
          </div>
        </div>
        <KnowledgeBaseChat appType={appType} />
      </div>
    );
  } else {
    panel = (
      <NavigateHelpPanel
        appType={appType}
        navItems={navItems}
        onClose={handleClose}
        onBack={offersHelpChoice ? () => setHelpMode(null) : handleClose}
        isWide={isWide}
        onToggleWide={toggleWide}
        launch={athenaLaunch}
        onLaunched={() => setAthenaLaunch(null)}
      />
    );
  }

  return <div className={`min-h-0 ${panelShell}`}>{panel}</div>;
}

// Re-export nav types for shell
export type { HelpNavItem };
