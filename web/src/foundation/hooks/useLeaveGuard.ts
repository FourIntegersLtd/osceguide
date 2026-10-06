"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Stops a person walking away from work they would lose by accident.
 *
 * While `guarded` is true (a live consultation, an unsaved draft), closing the
 * tab shows the browser's own warning, and a click on any link inside the app
 * is held back so the screen can ask first. `asking` is true while that
 * question is open.
 */
export function useLeaveGuard(guarded: boolean) {
  const router = useRouter();
  const [asking, setAsking] = useState(false);
  // Where the person was heading when the question was raised.
  const pendingHref = useRef<string | null>(null);

  useEffect(() => {
    if (!guarded) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const interceptLink = (event: MouseEvent) => {
      // Leave alone anything that is not a plain left click on a link to another page of this app.
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const target = event.target instanceof Element ? event.target : null;
      const anchor = target?.closest<HTMLAnchorElement>("a[href]");
      if (!anchor || anchor.target === "_blank" || anchor.hasAttribute("download")) return;
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin || url.href === window.location.href) return;
      event.preventDefault();
      event.stopPropagation();
      pendingHref.current = url.pathname + url.search + url.hash;
      setAsking(true);
    };
    window.addEventListener("beforeunload", warn);
    document.addEventListener("click", interceptLink, true);
    return () => {
      window.removeEventListener("beforeunload", warn);
      document.removeEventListener("click", interceptLink, true);
    };
  }, [guarded]);

  /** Go to a page, asking first while guarded. */
  const leaveTo = useCallback(
    (href: string) => {
      if (guarded) {
        pendingHref.current = href;
        setAsking(true);
        return;
      }
      router.push(href);
    },
    [guarded, router],
  );

  /** The person chose to stay: forget where they were going. */
  const stay = useCallback(() => {
    pendingHref.current = null;
    setAsking(false);
  }, []);

  /** The person chose to leave: close the question and hand back where they were going. */
  const confirmLeave = useCallback(() => {
    setAsking(false);
    return pendingHref.current;
  }, []);

  return { asking, leaveTo, stay, confirmLeave };
}
