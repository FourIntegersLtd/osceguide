"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  HiOutlineCheckCircle,
  HiOutlineEllipsisHorizontalCircle,
} from "react-icons/hi2";
import type { CoverageItem, CoverageUpdate } from "./api";

interface LiveCoverageFeedProps {
  coverage: CoverageUpdate | null;
  /** Live once the room connects. An empty feed means different things either side of that. */
  isLive?: boolean;
  /** Fewer rows where vertical space is scarce. */
  maxVisible?: number;
}

/**
 * What the doctor has demonstrated so far, newest first.
 *
 * Deliberately shows what has been *earned* rather than what is outstanding. A
 * visible list of missing items would turn the consultation into box-ticking,
 * which is the behaviour the exam exists to catch. There is also no red here:
 * these are coverage states, not grades, and the mark comes afterwards.
 */
const STATE_STYLES: Record<
  CoverageItem["state"],
  { ring: string; icon: string; Icon: typeof HiOutlineCheckCircle; label: string }
> = {
  covered: {
    ring: "border-osce-success-border bg-osce-success-bg",
    icon: "text-osce-success-icon",
    Icon: HiOutlineCheckCircle,
    label: "Covered",
  },
  partial: {
    ring: "border-osce-warning-border bg-osce-warning-bg",
    icon: "text-osce-warning-icon",
    Icon: HiOutlineEllipsisHorizontalCircle,
    label: "Partly",
  },
};

const LiveCoverageFeed: React.FC<LiveCoverageFeedProps> = ({
  coverage,
  isLive = false,
  maxVisible = 4,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Newest first: the thing that just happened is the thing worth seeing.
  const items = useMemo(
    () => [...(coverage?.items ?? [])].sort((a, b) => b.seq - a.seq),
    [coverage],
  );
  const visible = items.slice(0, maxVisible);
  const hidden = items.length - visible.length;

  // Rows enter at the top, so a learner who has scrolled down to read an older
  // quote would never see the one that just landed. Pin the viewport back to
  // the newest row whenever one arrives — the point of a live feed is the
  // thing that just happened.
  const listRef = useRef<HTMLDivElement>(null);
  const newestSeq = items[0]?.seq ?? null;
  useEffect(() => {
    if (newestSeq === null) return;
    listRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [newestSeq]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2">

      <div
        ref={listRef}
        className="min-h-0 flex-1 overflow-y-auto"
        aria-live="polite"
        aria-relevant="additions"
      >
        {items.length === 0 ? (
          <p className="text-osce-meta leading-relaxed text-b2c-text-muted">
            {/* A rubric with no live domains answers supported=false; "Listening" then hid that nothing would ever arrive. */}
            {coverage?.supported === false
              ? "Live marking isn't available for this station. Your feedback comes at the end."
              : isLive
              ? "Listening. Things you cover will appear here as you go."
              : "Your consultation will be marked here as it happens."}
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            <AnimatePresence initial={false}>
              {visible.map((item) => {
                const style = STATE_STYLES[item.state];
                const expanded = expandedId === item.competency_id;
                return (
                  <motion.li
                    key={item.competency_id}
                    layout
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.35 }}
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedId(expanded ? null : item.competency_id)
                      }
                      aria-expanded={expanded}
                      className={`flex w-full items-start gap-2.5 rounded-osce-md border px-3 py-2.5 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-osce-accent ${style.ring}`}
                    >
                      <style.Icon
                        className={`mt-0.5 h-[18px] w-[18px] shrink-0 ${style.icon}`}
                        aria-hidden="true"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block text-osce-data font-medium text-osce-ink-900">
                          {item.label}
                          {item.state === "partial" && (
                            <span className="ml-1 font-normal text-b2c-text-muted">
                              · partly
                            </span>
                          )}
                        </span>
                        {item.quote && (
                          <span
                            className={`block text-osce-meta italic text-b2c-text-secondary ${
                              expanded ? "" : "truncate"
                            }`}
                          >
                            &ldquo;{item.quote}&rdquo;
                          </span>
                        )}
                      </span>
                    </button>
                  </motion.li>
                );
              })}
            </AnimatePresence>
            {hidden > 0 && (
              <li className="px-3 pt-1 text-osce-meta text-b2c-text-muted">
                and {hidden} more
              </li>
            )}
          </ul>
        )}
      </div>

      <p className="shrink-0 text-osce-caption leading-snug text-b2c-text-muted">
        A guide while you practise, not your mark.
      </p>
    </div>
  );
};

export default LiveCoverageFeed;
