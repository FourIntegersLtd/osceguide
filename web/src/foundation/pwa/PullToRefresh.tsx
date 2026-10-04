"use client";

import { useEffect, useState } from "react";
import { MdRefresh } from "react-icons/md";
import { cn } from "@/foundation/ui";
import { useStandaloneDisplay } from "@/foundation/pwa/standalone";

/** How far the indicator has to be drawn down before letting go reloads. */
const TRIGGER_PX = 64;
const MAX_PX = 96;
/** The indicator moves at half the finger's speed, as a native one does. */
const RESISTANCE = 0.5;

/** Anywhere a pull must not reload: a live room, or an open dialog. */
const BLOCKED = "[data-live-room], [aria-modal='true']";

/** True when nothing between the touched element and the page is scrolled down. */
function scrolledToTop(target: EventTarget | null): boolean {
  if (window.scrollY > 0) return false;
  for (let node = target instanceof Element ? target : null; node; node = node.parentElement) {
    if (node.scrollTop > 0) return false;
  }
  return true;
}

/**
 * Pull down to reload, on every screen of the installed app.
 *
 * A browser tab has a reload button and Android's own pull-to-refresh; the
 * installed app has neither on iOS, and none on Android inside the shell,
 * which scrolls an inner region rather than the page. Mounted once at the root
 * so sign-in, the landing and every workspace screen behave the same.
 *
 * It stays out of the way where a reload would cost something: a live voice
 * room, where it would drop the session, and an open dialog.
 */
export function PullToRefresh() {
  const standalone = useStandaloneDisplay();
  const [pull, setPull] = useState(0);
  const [reloading, setReloading] = useState(false);

  useEffect(() => {
    if (!standalone) return undefined;
    let start: { x: number; y: number } | null = null;
    let distance = 0;

    const reset = () => {
      start = null;
      distance = 0;
      setPull(0);
    };

    const onTouchStart = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (event.touches.length !== 1 || !touch) return;
      if (document.querySelector(BLOCKED) || !scrolledToTop(event.target)) return;
      start = { x: touch.clientX, y: touch.clientY };
    };

    const onTouchMove = (event: TouchEvent) => {
      const touch = event.touches[0];
      if (!start || !touch) return;
      const dx = touch.clientX - start.x;
      const dy = touch.clientY - start.y;
      // A sideways swipe or an upward scroll is not a pull.
      if (dy <= 0 || Math.abs(dx) > dy) {
        reset();
        return;
      }
      distance = Math.min(MAX_PX, dy * RESISTANCE);
      setPull(distance);
    };

    const onTouchEnd = () => {
      if (start && distance >= TRIGGER_PX) {
        setReloading(true);
        window.location.reload();
        return;
      }
      reset();
    };

    document.addEventListener("touchstart", onTouchStart, { passive: true });
    document.addEventListener("touchmove", onTouchMove, { passive: true });
    document.addEventListener("touchend", onTouchEnd);
    document.addEventListener("touchcancel", reset);
    return () => {
      document.removeEventListener("touchstart", onTouchStart);
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onTouchEnd);
      document.removeEventListener("touchcancel", reset);
    };
  }, [standalone]);

  if (!standalone || (pull === 0 && !reloading)) return null;

  const armed = pull >= TRIGGER_PX;
  return (
    <div
      role="status"
      className="pointer-events-none fixed inset-x-0 top-[env(safe-area-inset-top,0px)] z-[110] flex justify-center"
    >
      <span
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-full border border-osce-border bg-osce-surface shadow-md",
          armed || reloading ? "text-osce-accent" : "text-osce-ink-500",
        )}
        style={{ transform: `translateY(${reloading ? TRIGGER_PX : pull}px)` }}
      >
        <MdRefresh
          className={cn("h-5 w-5", reloading && "animate-spin")}
          style={reloading ? undefined : { transform: `rotate(${pull * 3}deg)` }}
          aria-hidden
        />
        <span className="sr-only">{reloading ? "Reloading" : "Pull down to reload"}</span>
      </span>
    </div>
  );
}
