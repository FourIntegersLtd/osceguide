"use client";

import { useEffect, useState } from "react";

function format(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/** A clock that counts down from `from` seconds and then holds. At rest (and under reduced motion) it shows the start time. */
export function HomeClock({ from, className }: { from: number; className?: string }) {
  const [left, setLeft] = useState(from);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = setInterval(() => setLeft((n) => (n > 1 ? n - 1 : from)), 1000);
    return () => clearInterval(timer);
  }, [from]);

  return <span className={className}>{format(left)}</span>;
}
