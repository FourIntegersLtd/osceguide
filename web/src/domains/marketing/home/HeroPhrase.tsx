"use client";

import { useEffect, useState } from "react";

const PHRASES = [
  "is never tired",
  "is never busy",
  "is never unavailable",
  "is never late",
  "is never distracted",
  "never cancels",
  "never reschedules",
] as const;

/**
 * The hero's rotating phrase. The first phrase is the server-rendered one and
 * the only one under reduced motion, so the headline is complete at rest.
 */
export function HeroPhrase() {
  const [index, setIndex] = useState(0);
  const [shown, setShown] = useState(true);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let swap: ReturnType<typeof setTimeout> | undefined;
    const timer = setInterval(() => {
      setShown(false);
      swap = setTimeout(() => {
        setIndex((i) => (i + 1) % PHRASES.length);
        setShown(true);
      }, 280);
    }, 2600);
    return () => {
      clearInterval(timer);
      if (swap) clearTimeout(swap);
    };
  }, []);

  return (
    <span
      className={`inline-block text-site-brand transition-all duration-300 motion-reduce:transition-none ${
        shown ? "translate-y-0 opacity-100" : "translate-y-1 opacity-0"
      }`}
    >
      {PHRASES[index]}
    </span>
  );
}
