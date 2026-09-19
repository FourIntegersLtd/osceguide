"use client";

import { useEffect, type RefObject } from "react";
import { getFocusable } from "@/foundation/ui/modalDom";

interface FocusTrapOptions {
  enabled?: boolean;
  initialFocusRef?: RefObject<HTMLElement | null>;
  onEscape?: () => void;
}

/**
 * Keeps Tab focus inside `containerRef`, moves focus in on mount and restores
 * the previously focused element on unmount. Escape calls `onEscape`.
 */
export function useFocusTrap(
  containerRef: RefObject<HTMLElement | null>,
  { enabled = true, initialFocusRef, onEscape }: FocusTrapOptions = {},
) {
  useEffect(() => {
    if (!enabled) return;
    const container = containerRef.current;
    if (!container) return;
    const previouslyFocused =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const focusInitial = () => {
      const preferred = initialFocusRef?.current;
      if (preferred) {
        preferred.focus();
        return;
      }
      const focusable = getFocusable(container);
      const firstFocusable = focusable[0];
      if (firstFocusable) firstFocusable.focus();
      else {
        container.tabIndex = -1;
        container.focus();
      }
    };
    const frame = requestAnimationFrame(focusInitial);

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (onEscape) {
          event.stopPropagation();
          onEscape();
        }
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = getFocusable(container);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) {
        event.preventDefault();
        return;
      }
      const active = document.activeElement;
      if (event.shiftKey && (active === first || !container.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKeyDown);
      if (previouslyFocused && document.contains(previouslyFocused)) {
        previouslyFocused.focus();
      }
    };
  }, [containerRef, enabled, initialFocusRef, onEscape]);
}
