"use client";

import { useEffect } from "react";

/**
 * Registers `public/sw.js`, whose only job is the offline page.
 *
 * Production only: in development a worker sits between the browser and the
 * dev server and makes a failed compile look like being offline.
 */
export function ServiceWorkerRegistration() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/", updateViaCache: "none" }).catch(() => {
      // No worker means no offline page, which is how the site already behaved.
    });
  }, []);
  return null;
}
