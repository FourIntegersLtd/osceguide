"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { jumpScrollTop, readingBand, stuckBottom } from "@/capabilities/media/jumpGeometry";
import type { SummaryGroups } from "@/capabilities/media/summaryGroups";

const sectionId = (key: string) => `summary-${key}`;

/** The element that actually scrolls the page: the app shell scrolls an inner div, not the window. */
function scroller(el: HTMLElement | null): Element {
  for (let node = el?.parentElement; node; node = node.parentElement) {
    if (/(auto|scroll)/.test(getComputedStyle(node).overflowY)) return node;
  }
  return document.scrollingElement ?? document.documentElement;
}

/** Where the sticky block holding `el` ends once it sticks (0 when nothing sticks). */
function headerBottom(el: HTMLElement | null): number {
  for (let node = el; node; node = node.parentElement) {
    const style = getComputedStyle(node);
    if (style.position !== "sticky") continue;
    const box = scroller(node);
    const top = box === document.scrollingElement ? 0 : box.getBoundingClientRect().top;
    return stuckBottom(top, parseFloat(style.top) || 0, node.getBoundingClientRect().height);
  }
  return 0;
}

/**
 * The jump index's behaviour: a click scrolls smoothly so the heading lands just under the
 * sticky header and is active at once; after that the active entry follows the reader. One
 * IntersectionObserver watches the headings through a band that starts below the stuck header.
 *
 * A link to a group not yet on the page asks `onShowAll` for the rest, then scrolls to it.
 */
export function useJumpIndex(groups: SummaryGroups, onShowAll?: () => void) {
  const navRef = useRef<HTMLElement>(null);
  const settleTimer = useRef<number | undefined>(undefined);
  const jumping = useRef(false);
  const visible = useRef(new Set<string>());
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    const keys = Object.keys(groups).sort();
    visible.current.clear();
    const follow = () => setActive(keys.find((key) => visible.current.has(key)) ?? null);
    const observer = new IntersectionObserver(
      (entries) => {
        for (const { target, isIntersecting } of entries) {
          const key = keys.find((k) => sectionId(k) === target.id);
          if (key === undefined) continue;
          if (isIntersecting) visible.current.add(key);
          else visible.current.delete(key);
        }
        if (!jumping.current) follow();
      },
      { rootMargin: readingBand(headerBottom(navRef.current)) },
    );
    for (const key of keys) {
      const el = document.getElementById(sectionId(key));
      if (el) observer.observe(el);
    }
    const settle = () => {
      jumping.current = false;
      follow();
    };
    // scrollend does not bubble from an element, so listen in the capture phase.
    document.addEventListener("scrollend", settle, true);
    return () => {
      observer.disconnect();
      window.clearTimeout(settleTimer.current);
      document.removeEventListener("scrollend", settle, true);
    };
  }, [groups]);

  const jump = useCallback(
    (key: string) => {
      setActive(key);
      const scroll = () => {
        const section = document.getElementById(sectionId(key));
        if (!section) return;
        jumping.current = true;
        const box = scroller(section);
        box.scrollTo({
          top: jumpScrollTop(section.getBoundingClientRect().top, box.scrollTop, headerBottom(navRef.current)),
          behavior: "smooth",
        });
        // scrollend never fires on older Safari, nor when nothing scrolls: release the lock anyway.
        window.clearTimeout(settleTimer.current);
        settleTimer.current = window.setTimeout(() => (jumping.current = false), 1000);
      };
      if (document.getElementById(sectionId(key))) return scroll();
      onShowAll?.();
      requestAnimationFrame(scroll); // after the show-all render commits
    },
    [onShowAll],
  );

  return { navRef, active, jump };
}
