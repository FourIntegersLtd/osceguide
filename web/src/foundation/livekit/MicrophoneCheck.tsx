"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineExclamationTriangle,
  HiOutlineMicrophone,
} from "react-icons/hi2";
import { Button, cn } from "@/foundation/ui";
import { b2cCardPlain } from "@/foundation/ui/productTokens";

/** Why the microphone could or could not be opened. */
type MicCheckStatus = "granted" | "denied" | "no-device" | "in-use" | "unsupported" | "error";

interface MicCheckResult {
  status: MicCheckStatus;
  deviceLabel: string | null;
}

type BrowserFamily = "chrome" | "safari" | "firefox" | "edge" | "other";

/** Turn a getUserMedia refusal into the reason a person can act on. */
function statusFromMediaError(error: unknown): MicCheckStatus {
  const name = error instanceof DOMException || error instanceof Error ? error.name : "";
  switch (name) {
    case "NotAllowedError":
    case "PermissionDeniedError":
    case "SecurityError":
      return "denied";
    case "NotFoundError":
    case "DevicesNotFoundError":
    case "OverconstrainedError":
      return "no-device";
    case "NotReadableError":
    case "TrackStartError":
    case "AbortError":
      return "in-use";
    default:
      return "error";
  }
}

/**
 * Open the microphone once and release it straight away.
 *
 * Holding the stream would light the browser's recording indicator while the
 * candidate is still reading the rules, so the track is stopped as soon as the
 * device's label has been read.
 */
async function checkMicrophoneAccess(): Promise<MicCheckResult> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return { status: "unsupported", deviceLabel: null };
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const deviceLabel = stream.getAudioTracks()[0]?.label || null;
    stream.getTracks().forEach((track) => track.stop());
    return { status: "granted", deviceLabel };
  } catch (error) {
    return { status: statusFromMediaError(error), deviceLabel: null };
  }
}

function detectBrowser(userAgent: string): BrowserFamily {
  const agent = userAgent.toLowerCase();
  if (agent.includes("edg/")) return "edge";
  if (agent.includes("firefox")) return "firefox";
  if (agent.includes("chrome") || agent.includes("crios")) return "chrome";
  if (agent.includes("safari")) return "safari";
  return "other";
}

/** Where each browser keeps the switch that unblocks a site's microphone. */
const UNBLOCK_STEPS: Record<BrowserFamily, string> = {
  chrome:
    "Click the lock or tune icon in the address bar, set Microphone to Allow, then test again.",
  edge: "Click the lock icon in the address bar, set Microphone to Allow, then test again.",
  firefox: "Click the microphone icon in the address bar, remove the block, then test again.",
  safari:
    "Open Safari › Settings for This Website (or the “aA” menu on iPhone), set Microphone to Allow, then test again.",
  other:
    "Open your browser's site settings, allow the microphone for this site, then test again.",
};

function helpCopy(status: MicCheckStatus, browser: BrowserFamily): { title: string; body: string } {
  switch (status) {
    case "granted":
      return { title: "Microphone ready", body: "The patient will be able to hear you." };
    case "denied":
      return {
        title: "Microphone access is blocked",
        body: `OSCE Guide needs your microphone so the patient can hear you. ${UNBLOCK_STEPS[browser]}`,
      };
    case "no-device":
      return {
        title: "No microphone found",
        body: "Connect a microphone or headset, then test again.",
      };
    case "in-use":
      return {
        title: "Your microphone is being used by another app",
        body: "Close other apps that use it (for example Teams or Zoom), then test again.",
      };
    case "unsupported":
      return {
        title: "This browser can't access your microphone",
        body: "Open OSCE Guide in a recent version of Chrome, Edge, Safari or Firefox.",
      };
    default:
      return {
        title: "We couldn't check your microphone",
        body: "Refresh the page and try again. If it keeps failing, try another browser.",
      };
  }
}

/**
 * The pre-flight card on a session's rules page: it asks for the microphone as
 * soon as it mounts, says per browser why that failed, and offers "Test again".
 *
 * `useMicPreflight` only reads the permission and asks when clicked, which is
 * right inside a room. Before a session the retiring client asked straight
 * away so the Start button could be gated on the answer; this is that card.
 * It re-runs when the person changes the permission from the browser's own UI.
 */
export function MicrophoneCheck({
  onReadyChange,
  className = "",
  variant = "card",
}: {
  /** Called whenever readiness changes; gate the Start button on it. */
  onReadyChange?: (ready: boolean) => void;
  className?: string;
  /** `plain` drops the card border to sit inside another card. */
  variant?: "card" | "plain";
}) {
  const [result, setResult] = useState<MicCheckResult | null>(null);
  const [isChecking, setIsChecking] = useState(false);
  const mounted = useRef(true);
  const browser = useMemo(
    () => detectBrowser(typeof navigator === "undefined" ? "" : navigator.userAgent),
    [],
  );

  const check = useCallback(async () => {
    const next = await checkMicrophoneAccess();
    if (!mounted.current) return;
    setResult(next);
    setIsChecking(false);
  }, []);

  const run = useCallback(() => {
    setIsChecking(true);
    void check();
  }, [check]);

  useEffect(() => {
    mounted.current = true;
    // The permission lives outside React, so the check starts on mount.
    void check();
    return () => {
      mounted.current = false;
    };
  }, [check]);

  // Re-run when the permission is changed from the address bar.
  useEffect(() => {
    if (typeof navigator === "undefined" || !navigator.permissions?.query) return undefined;
    let permission: PermissionStatus | null = null;
    const onChange = () => run();
    navigator.permissions
      .query({ name: "microphone" as PermissionName })
      .then((status) => {
        permission = status;
        status.addEventListener("change", onChange);
      })
      .catch(() => {
        // Safari has no microphone permission query; "Test again" still works.
      });
    return () => permission?.removeEventListener("change", onChange);
  }, [run]);

  const isReady = result?.status === "granted";
  useEffect(() => {
    onReadyChange?.(isReady);
  }, [isReady, onReadyChange]);

  const copy = result ? helpCopy(result.status, browser) : null;
  const tone = !result ? "checking" : isReady ? "ok" : "problem";

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(variant === "card" ? b2cCardPlain : "", "flex items-start gap-3 p-4", className)}
    >
      <span
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          tone === "ok" && "bg-osce-success-bg text-osce-success-text",
          tone === "problem" && "bg-osce-warning-bg text-osce-warning-text",
          tone === "checking" && "bg-b2c-surface-muted text-b2c-text-muted",
        )}
      >
        {tone === "ok" ? (
          <HiOutlineCheckCircle className="h-4 w-4" aria-hidden />
        ) : tone === "problem" ? (
          <HiOutlineExclamationTriangle className="h-4 w-4" aria-hidden />
        ) : (
          <HiOutlineMicrophone className="h-4 w-4" aria-hidden />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-osce-body font-semibold text-osce-ink-900">
          {copy?.title ?? "Checking your microphone…"}
        </p>
        <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
          {copy?.body ??
            "Your browser will ask for permission. Choose Allow so the patient can hear you."}
        </p>
        {result?.deviceLabel ? (
          <p className="mt-1 text-osce-caption text-b2c-text-muted">Using: {result.deviceLabel}</p>
        ) : null}
        {tone !== "ok" ? (
          <div className="mt-3">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={run}
              isLoading={isChecking}
            >
              <HiOutlineArrowPath className="mr-1.5 h-4 w-4" aria-hidden />
              Test again
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
