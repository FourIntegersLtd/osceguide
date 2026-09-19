"use client";

import { useEffect, useRef } from "react";

const STATE_KEY = "osceModal";
/** Ids of modals that pushed a history entry, innermost last. */
const openStack: string[] = [];

let counter = 0;
const nextId = () => `modal-${Date.now()}-${(counter += 1)}`;

/**
 * Pushes a history entry while a modal is open so the browser / Android Back
 * button closes the modal instead of leaving the page. Nested modals stack.
 */
export function useModalHistory(enabled: boolean, onClose: (() => void) | undefined) {
  const idRef = useRef<string>("");
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!enabled || typeof window === "undefined" || !onCloseRef.current) return;
    const id = nextId();
    idRef.current = id;
    openStack.push(id);
    window.history.pushState(
      { ...(window.history.state ?? {}), [STATE_KEY]: id },
      "",
    );
    let closedByPop = false;

    const onPopState = () => {
      const top = openStack[openStack.length - 1];
      if (top !== id) return;
      closedByPop = true;
      openStack.pop();
      onCloseRef.current?.();
    };
    window.addEventListener("popstate", onPopState);

    return () => {
      window.removeEventListener("popstate", onPopState);
      if (closedByPop) return;
      const index = openStack.lastIndexOf(id);
      if (index !== -1) openStack.splice(index, 1);

      // Closed programmatically: peel the modal flag without history.back().
      // back() fires popstate and can reset App Router client state (e.g. station tabs).
      const current = window.history.state as Record<string, unknown> | null;
      if (current && current[STATE_KEY] === id) {
        const rest = { ...current };
        delete rest[STATE_KEY];
        window.history.replaceState(rest, "");
      }
    };
  }, [enabled]);
}
