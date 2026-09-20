"use client";

import { useCallback, useState } from "react";
import { usePathname } from "next/navigation";
import { LuCircleHelp, LuX } from "react-icons/lu";
import { Alert, Button, Spinner } from "@/foundation/ui";
import { AgentTile, VoiceRoom, useMicPreflight, type RoomGrant } from "@/foundation/livekit";
import { errorMessage } from "@/foundation/hooks";
import { assistantSurfaceFor } from "@/capabilities/surface";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  assistantVoiceToken,
  buildClientContext,
  startAssistantSession,
} from "@/capabilities/help/api";

export interface HelpNavItem {
  key: string;
  label: string;
  path: string;
}

/**
 * The help panel, docked to whichever shell renders it.
 *
 * It takes the shell's navigation as a prop rather than importing it, which is
 * the whole reason this works on four surfaces: the panel never learns that
 * institutions have sittings or that consumers have mocks, it just forwards
 * what it was handed and lets the backend's content packs answer.
 */
export function HelpPanel({
  navItems = [],
  initialOpen = false,
}: {
  navItems?: HelpNavItem[];
  /** When true, open the dialog on mount (used after a lazy import). */
  initialOpen?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);

  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 shadow-lg"
        aria-haspopup="dialog"
      >
        <LuCircleHelp className="h-4 w-4" aria-hidden /> Help
      </Button>
      {open && <HelpDialog navItems={navItems} onClose={() => setOpen(false)} />}
    </>
  );
}

function HelpDialog({ navItems, onClose }: { navItems: HelpNavItem[]; onClose: () => void }) {
  const { surface } = useSurface();
  const pathname = usePathname();
  const mic = useMicPreflight();
  const [grant, setGrant] = useState<RoomGrant | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const start = useCallback(async () => {
    setStarting(true);
    setError(null);
    try {
      if (mic.status !== "ready") await mic.request();
      const context = buildClientContext({
        surface: assistantSurfaceFor(surface),
        pathname,
        navItems,
      });
      const session = await startAssistantSession("help", context);
      setGrant(await assistantVoiceToken(session.id));
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setStarting(false);
    }
  }, [mic, navItems, pathname, surface]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Help"
      className="fixed inset-0 z-50 flex items-end justify-end bg-ink/20 p-4 sm:p-6"
    >
      <div className="flex w-full max-w-sm flex-col gap-4 rounded-panel border border-border bg-surface p-5 shadow-xl">
        <header className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">Ask for help</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close help"
            className="rounded-control p-1 text-ink-muted hover:bg-surface-raised hover:text-ink"
          >
            <LuX className="h-4 w-4" aria-hidden />
          </button>
        </header>

        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        {mic.message && <Alert tone="warning">{mic.message}</Alert>}

        {grant ? (
          <VoiceRoom
            grant={grant}
            onDisconnected={() => setGrant(null)}
            onError={(cause) => setError(cause)}
          >
            <AgentTile name="Assistant" detail="Ask about anything on this screen" />
            <Button variant="danger" className="mt-3 w-full" onClick={() => setGrant(null)}>
              End
            </Button>
          </VoiceRoom>
        ) : (
          <>
            <p className="text-sm text-ink-muted">
              Speak your question. The assistant knows which screen you are on.
            </p>
            <Button onClick={start} disabled={starting} className="w-full">
              {starting ? <Spinner label="Starting" /> : "Start talking"}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
