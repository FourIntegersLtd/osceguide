"use client";

import { useCallback, useEffect, useState } from "react";

export type MicStatus = "checking" | "ready" | "denied" | "missing" | "insecure";

export interface MicPreflight {
  status: MicStatus;
  /** Ask the browser for permission. Safe to call from a click handler. */
  request: () => Promise<void>;
  message: string | null;
}

/**
 * Whether this browser can actually hear the candidate.
 *
 * The old consumer client started a consultation without checking, so a denied
 * or absent microphone produced a session where the patient waited in silence
 * and the candidate could not tell why. Every voice surface checks first now.
 */
export function useMicPreflight(enabled = true): MicPreflight {
  const [status, setStatus] = useState<MicStatus>("checking");

  const evaluate = useCallback(async () => {
    if (typeof window === "undefined") return;
    // getUserMedia is absent outside a secure context, which is the usual
    // cause on a LAN address rather than localhost.
    if (!window.isSecureContext) {
      setStatus("insecure");
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      setStatus("missing");
      return;
    }
    try {
      const permissions = navigator.permissions;
      if (permissions?.query) {
        const result = await permissions.query({ name: "microphone" as PermissionName });
        if (result.state === "granted") {
          setStatus("ready");
          return;
        }
        if (result.state === "denied") {
          setStatus("denied");
          return;
        }
      }
    } catch {
      // Firefox rejects a microphone permission query; fall through to asking.
    }
    setStatus("checking");
  }, []);

  const request = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Released immediately: holding it lights the recording indicator while
      // the candidate is still reading the brief.
      stream.getTracks().forEach((track) => track.stop());
      setStatus("ready");
    } catch (cause) {
      setStatus(cause instanceof DOMException && cause.name === "NotFoundError" ? "missing" : "denied");
    }
  }, []);

  useEffect(() => {
    if (enabled) void evaluate();
  }, [enabled, evaluate]);

  return { status, request, message: MESSAGES[status] };
}

const MESSAGES: Record<MicStatus, string | null> = {
  checking: null,
  ready: null,
  denied:
    "Your browser is blocking the microphone. Allow it in the address bar, then try again.",
  missing: "We could not find a microphone. Plug one in or switch device, then try again.",
  insecure:
    "Microphones only work over a secure connection. Open this page on https or on localhost.",
};
