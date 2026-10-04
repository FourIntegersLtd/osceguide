"use client";

import { useEffect, useRef } from "react";
import { useToast } from "@/foundation/hooks";

/** No more than one check in this long, however often the app is reopened. */
const MIN_CHECK_GAP_MS = 5 * 60 * 1000;
const TOAST_ID = "app-update-available";

/** The commit the server is running now; null when it cannot be read. */
async function deployedCommit(): Promise<string | null> {
  try {
    // Our own `/version` route, not the platform API, so not `platformRequest`.
    const response = await fetch("/version", { cache: "no-store" });
    if (!response.ok) return null;
    const body = (await response.json()) as { commit?: string };
    return body.commit || null;
  } catch {
    return null;
  }
}

/**
 * Says when a newer build has been deployed than the one on screen.
 *
 * An installed app is rarely closed: the phone suspends it and brings the same
 * page back days later, still running the build it was opened with. Each time
 * it returns to the foreground this compares `/version` with the commit it
 * first saw, and offers a reload when they differ. It never reloads on its
 * own, and it says nothing during a live voice room.
 */
export function UpdateNotice() {
  const toast = useToast();
  // Through a ref: the toast context changes whenever any toast shows, and
  // re-running the effect would forget which commit this page was loaded with.
  const showToast = useRef(toast.show);
  useEffect(() => {
    showToast.current = toast.show;
  });

  useEffect(() => {
    let loaded: string | null = null;
    let lastCheck = 0;
    let announced = false;

    const check = async () => {
      if (announced || document.visibilityState !== "visible") return;
      if (Date.now() - lastCheck < MIN_CHECK_GAP_MS) return;
      lastCheck = Date.now();
      const current = await deployedCommit();
      if (!current) return;
      if (!loaded) {
        loaded = current;
        return;
      }
      if (current === loaded) return;
      if (document.querySelector("[data-live-room]")) {
        // Ask again the next time the app comes forward, once the session is over.
        lastCheck = 0;
        return;
      }
      announced = true;
      showToast.current({
        id: TOAST_ID,
        tone: "info",
        title: "A new version is available",
        message: "Reload to get the latest OSCE Guide.",
        persistent: true,
        action: { label: "Reload", onClick: () => window.location.reload() },
      });
    };

    void check();
    document.addEventListener("visibilitychange", check);
    return () => document.removeEventListener("visibilitychange", check);
  }, []);

  return null;
}
