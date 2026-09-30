"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { IconType } from "react-icons";
import { HiOutlineInformationCircle } from "react-icons/hi2";
import type { MetricTone } from "@/foundation/attribution/viewModel";

/** Semantic classes per tone, so the platform skin owns the actual colour. */
const TONES: Record<MetricTone, { well: string; value: string }> = {
  blue: { well: "bg-accent-subtle text-accent", value: "text-accent" },
  amber: { well: "bg-warning-subtle text-warning", value: "text-warning" },
  orange: { well: "bg-warning-subtle text-warning", value: "text-warning" },
  emerald: { well: "bg-success-subtle text-success", value: "text-success" },
};

/**
 * One KPI: an icon well, a label, a tabular value and an info button.
 *
 * The definition opens on tap rather than hover so a phone can reach it, and
 * closes on an outside tap or Escape.
 */
export function MetricCard({
  label,
  value,
  icon: Icon,
  tone,
  tooltip,
}: {
  label: string;
  value: string;
  icon: IconType;
  tone: MetricTone;
  tooltip?: string;
}) {
  const styles = TONES[tone];
  const tooltipId = useId();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div
      ref={rootRef}
      className="relative flex h-full min-h-[7rem] flex-col rounded-osce-lg border border-border bg-surface p-3 sm:min-h-[7.5rem] sm:p-4"
    >
      <div className="flex items-start justify-between gap-2">
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md ${styles.well}`}
        >
          <Icon className="h-[18px] w-[18px]" aria-hidden />
        </span>
        {tooltip ? (
          <button
            type="button"
            onClick={() => setOpen((current) => !current)}
            aria-expanded={open}
            aria-controls={tooltipId}
            aria-label={`What "${label}" means`}
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-ink-subtle hover:bg-canvas hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
          >
            <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
          </button>
        ) : null}
      </div>
      <p className="mt-auto text-osce-caption font-medium text-ink-subtle">{label}</p>
      <p
        className={`mt-1 truncate font-heading text-osce-title font-semibold tabular-nums ${styles.value}`}
        title={value}
        aria-describedby={tooltip ? tooltipId : undefined}
      >
        {value}
      </p>
      {tooltip ? (
        <div
          id={tooltipId}
          role="note"
          hidden={!open}
          className="absolute left-2 right-2 top-[calc(100%-0.5rem)] z-20 rounded-osce-lg border border-border bg-surface px-3 py-2 text-osce-meta leading-snug text-ink-muted shadow-lg"
        >
          {tooltip}
        </div>
      ) : null}
    </div>
  );
}

/** A definition as a term and its plain-English meaning, with an icon. */
export function DefinitionCard({
  term,
  detail,
  icon: Icon,
  tone,
}: {
  term: string;
  detail: string;
  icon: IconType;
  tone: MetricTone;
}) {
  return (
    <div className="rounded-osce-lg border border-border bg-surface p-4">
      <div className="flex gap-3">
        <span
          className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md ${TONES[tone].well}`}
        >
          <Icon className="h-[18px] w-[18px]" aria-hidden />
        </span>
        <div className="min-w-0">
          <dt className="text-osce-body font-medium text-ink">{term}</dt>
          <dd className="mt-1 text-osce-meta text-ink-muted">{detail}</dd>
        </div>
      </div>
    </div>
  );
}
