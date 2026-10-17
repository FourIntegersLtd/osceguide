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
import { helpType } from "@/foundation/ui/helpType";
import { KnowledgeBaseChat } from "./KnowledgeBaseChat";
import HelpArticleBrowse from "@/capabilities/help/HelpArticleBrowse";
import { AthenaFab } from "@/capabilities/help/AthenaFab";
import { athenaVoiceAllowed, helpPersona } from "@/capabilities/help/helpPersona";
import {
  assistantVoiceToken,
  buildClientContext,
  readAthenaLaunch,
  startAssistantSession,
  type AssistantSessionType,
  type AthenaLaunch,
  type AthenaTopic,
  type HelpNavItem,
} from "@/capabilities/help/api";

const helpHeaderIconBtn =
  "inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md text-white/80 transition-colors hover:bg-white/10 hover:text-white sm:h-9 sm:w-9";

const helpPanelFooter =
  "shrink-0 border-t border-osce-border-light bg-osce-surface p-3 pb-[max(0.75rem,env(safe-area-inset-bottom,0px))] sm:p-4 lg:pb-4";

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
  voice,
}: {
  onChooseNavigate: () => void;
  onChooseKnowledge: () => void;
  onClose: () => void;
  isWide: boolean;
  onToggleWide: () => void;
  voice: boolean;
}) {
  return (
    <div className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-osce-surface text-osce-body lg:max-h-none">
      <div className="flex shrink-0 items-center justify-between bg-gradient-to-r from-osce-accent to-osce-accent-hover px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="rounded-full bg-white/20 p-1.5">
            <BsInfoCircleFill className="h-4 w-4 text-white" />
          </div>
          <span className={helpType.barTitle}>{helpPersona(voice).name}</span>
        </div>
        <div className="flex items-center gap-0.5">
          <HelpWideToggle isWide={isWide} onToggle={onToggleWide} />
          <button type="button" onClick={onClose} className={helpHeaderIconBtn} aria-label="Close">
            <IoMdClose className="h-5 w-5" color="white" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-4">
        {voice ? <AthenaIdentity className="mb-4" /> : null}
        <h3 className={helpType.title}>
          How can we help?
        </h3>
        <p className={`mt-0.5 ${helpType.support}`}>Choose one option to get started</p>

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
                  <span className={`block ${helpType.rowTitle}`}>
                    {voice ? "Talk to Athena" : "Browse the guides"}
                  </span>
                  <span className={`mt-0.5 block ${helpType.support}`}>
                    {voice ? "Ask about your practice, a condition or the app, or browse the guides" : "Search the help articles for the app and your account"}
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
                  <span className={`block ${helpType.rowTitle}`}>
                    Ask our knowledge base
                  </span>
                  <span className={`mt-0.5 block ${helpType.support}`}>
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
  examCode,
  navItems,
  onClose,
  onBack,
  isWide,
  onToggleWide,
  launch,
  onLaunched,
  voice,
}: {
  examCode?: string;
  navItems: HelpNavItem[];
  onClose: () => void;
  onBack: () => void;
  isWide: boolean;
  onToggleWide: () => void;
  launch: AthenaLaunch | null;
  onLaunched: () => void;
  voice: boolean;
}) {
  const { surface } = useSurface();
  const pathname = usePathname();
  const mic = useMicPreflight();
  const screenGuidanceAvailable = useScreenUiGuidance();
  const [voiceHelpIntent, setVoiceHelpIntent] = useState<"faq" | "guide">("faq");
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  // A help article Athena suggested, opened in place above the call.
  const [helpArticle, setHelpArticle] = useState<string | null>(null);

  // Talking to Athena is a `dashboard` session wherever it starts: the one
  // with her memory and the knowledge base. `help` is only the on-screen guide.
  // A `topic` is what they pressed "Discuss with Athena" on; she opens with it.
  const startVoice = useCallback(async (intent: "faq" | "guide" = "faq", sessionType: AssistantSessionType = "dashboard", topic: AthenaTopic | null = null) => {
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
      const session = await startAssistantSession(sessionType, context, {
        help: { voice_help_intent: intent, screen_ui_guidance: intent === "guide" && screenGuidanceAvailable },
        topic,
      });
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
    if (!voice) return;
    const onboarding = launch.kind === "onboarding";
    void startVoice(onboarding ? "guide" : "faq", onboarding ? "onboarding" : "dashboard", onboarding ? null : launch.topic);
  }, [launch, onLaunched, startVoice, voice]);

  const endVoice = useCallback(() => {
    setGrant(null);
    setHelpArticle(null);
  }, []);

  const inCall = Boolean(grant);

  return (
    <div {...uiGuidanceIgnoreProps} className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-osce-surface text-osce-body shadow-lg lg:max-h-none">
      <div className="flex shrink-0 items-center justify-between bg-gradient-to-r from-osce-accent to-osce-accent-hover px-4 py-3">
        <div className="flex items-center gap-2">
          <button type="button" onClick={onBack} className={helpHeaderIconBtn} aria-label="Back">
            <IoArrowBack className="h-5 w-5" />
          </button>
          <div className="rounded-full bg-white/20 p-1.5">
            <BsInfoCircleFill className="h-4 w-4 text-white" />
          </div>
          <span className={helpType.barTitle}>{helpPersona(voice).name}</span>
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

        {!inCall || helpArticle ? (
          <HelpArticleBrowse key={helpArticle ?? "browse"} examCode={examCode} initialArticle={helpArticle ?? undefined} />
        ) : null}

        {!inCall && voice && <div className="mb-3 hidden shrink-0 flex-col items-center justify-center lg:mt-6 lg:flex"><AthenaIdentity description="Or ask Athena by voice below" /></div>}

        {inCall ? (
          <VoiceRoom grant={grant} onDisconnected={() => endVoice()} onError={setError}>
            <HelpVoiceContent voiceHelpIntent={voiceHelpIntent} onOpenHelpArticle={setHelpArticle} />
          </VoiceRoom>
        ) : null}
      </div>

      <div className={`${helpPanelFooter} mt-auto`}>
        {!inCall && voice ? (
          <div className="mb-3 lg:hidden">
            <AthenaIdentity description="Or ask Athena by voice below" />
          </div>
        ) : null}
        {!inCall && voice ? (
          <Button
            type="button"
            variant="primary"
            size="md"
            fullWidth
            onClick={() => startVoice()}
            disabled={starting}
            className="mx-auto gap-1.5 sm:gap-2"
          >
            {starting ? (
              <div className="flex items-center justify-center gap-1.5">
                <Spinner label="Connecting" className="text-current" />
                <span>Connecting…</span>
              </div>
            ) : (
              <>
                <FiPhoneCall className="h-4 w-4" />
                <span>Talk to Athena</span>
              </>
            )}
          </Button>
        ) : inCall ? (
          <button
            type="button"
            className={`${b2cLivekitEndButton} mx-auto w-full gap-1.5 sm:gap-2`}
            onClick={endVoice}
          >
            <HiPhoneXMark className="h-4 w-4" />
            <span>End conversation</span>
          </button>
        ) : null}
        {!inCall && voice && screenGuidanceAvailable && <Button type="button" variant="secondary" size="md" fullWidth disabled={starting} className="mt-2 gap-1.5" onClick={() => startVoice("guide", "help")}><LuMousePointer2 className="h-4 w-4" /><span>Guide me on screen</span></Button>}
        <div className="mt-2 px-1 text-center sm:px-2">
          <p className={helpType.support}>
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
  /** Whose help to show. Defaults to the signed-in person's exam; with none, the general guides. */
  examCode?: string;
  /** A launch that arrived before this component loaded (see `LazyB2CHelpDock`); opens on it at mount. */
  initialLaunch?: AthenaLaunch | null;
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
  examCode: examCodeOverride,
  initialLaunch = null,
}: B2CHelpDockProps) {
  const { session } = useSession();
  const voice = athenaVoiceAllowed(usePathname());
  const { code, settings } = useCurrentExam();
  const examCode = (examCodeOverride ?? code)?.toLowerCase();
  // Whether there is a choice to offer at all (`settings.help_modes`,
  // `app/core/exam_settings.py`). An exam that only lists one mode skips the
  // choice screen and opens straight into it.
  const { offersChoice: offersHelpChoice, opensDirectlyOnKnowledge } = helpModeChoice(settings);
  const [helpMode, setHelpMode] = useState<HelpMode>(initialLaunch ? "navigate" : null);
  const [athenaLaunch, setAthenaLaunch] = useState<AthenaLaunch | null>(initialLaunch);

  useEffect(() => {
    const open = (event: Event) => {
      setIsExpanded(true);
      setHelpMode("navigate");
      setAthenaLaunch(readAthenaLaunch((event as CustomEvent<unknown>).detail));
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

  if (!isExpanded) return <AthenaFab onClick={() => setIsExpanded(true)} />;

  const panelShell =
    "fixed inset-0 z-50 flex h-[100dvh] max-h-[100dvh] w-full flex-col lg:static lg:z-auto lg:h-full lg:max-h-none lg:w-auto";

  let panel: ReactNode;
  if (helpMode === null && offersHelpChoice) {
    panel = (
      <HelpChoiceScreen
        onClose={handleClose}
        onChooseNavigate={() => setHelpMode("navigate")}
        onChooseKnowledge={() => setHelpMode("knowledge")}
        isWide={isWide}
        onToggleWide={toggleWide}
        voice={voice}
      />
    );
  } else if (helpMode === "knowledge" || (helpMode === null && opensDirectlyOnKnowledge)) {
    panel = (
      <div {...uiGuidanceIgnoreProps} className="flex h-full min-h-0 w-full max-h-full flex-col overflow-hidden border-l border-osce-border bg-osce-surface text-osce-body shadow-lg lg:max-h-none">
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
            <span className={helpType.barTitle}>Knowledge base</span>
          </div>
          <div className="flex items-center gap-0.5">
            <HelpWideToggle isWide={isWide} onToggle={toggleWide} />
            <button type="button" onClick={handleClose} className={helpHeaderIconBtn} aria-label="Close">
              <IoMdClose className="h-5 w-5" color="white" />
            </button>
          </div>
        </div>
        <KnowledgeBaseChat examCode={examCode} />
      </div>
    );
  } else {
    panel = (
      <NavigateHelpPanel
        examCode={examCode}
        navItems={navItems}
        onClose={handleClose}
        onBack={offersHelpChoice ? () => setHelpMode(null) : handleClose}
        isWide={isWide}
        onToggleWide={toggleWide}
        launch={athenaLaunch}
        onLaunched={() => setAthenaLaunch(null)}
        voice={voice}
      />
    );
  }

  return <div className={`min-h-0 ${panelShell}`}>{panel}</div>;
}

export type { HelpNavItem };
