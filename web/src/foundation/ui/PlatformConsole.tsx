"use client";

import { useState } from "react";
import Link from "next/link";
import { HiOutlineChevronRight } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";
import { Badge } from "@/foundation/ui/Badge";
import { Button } from "@/foundation/ui/Button";
import { EmptyState } from "@/foundation/ui/EmptyState";
import { cardScrollBody } from "@/foundation/ui/Card";
import { boardCardClipped } from "@/foundation/ui/boardKit";
import * as b2bTokens from "@/foundation/ui/b2bTokens";

/**
 * Staff console layout primitives.
 *
 * The console used to borrow the consumer B2C card chrome directly — a bare
 * title floating over a `Card`, cramped rows, one long column on a detail
 * screen. This is the console's own kit: panels with the header inside them,
 * a KPI grid, a sticky action rail on detail screens. Tokens only — the
 * `text-osce-*` type scale for sizes and semantic colours (`text-ink`,
 * `border-border`, `bg-surface`), so the platform skin owns the palette.
 * No raw sizes, no black.
 */

/**
 * A part of a long form that folds from its header: one slide, one group of
 * lines, one group of fields. It sits inside a `Panel` and shares its tinted
 * header, so every editable part of the console reads and folds the same way.
 * A folded body stays mounted, so it keeps what was typed.
 */
export function FoldSection({
  title,
  description,
  number,
  meta,
  actions,
  defaultOpen = true,
  board = false,
  children,
}: {
  title: string;
  /** A line of help shown at the top of the open body. */
  description?: string;
  /** A position in a list, drawn as a chip before the title. */
  number?: number;
  /** Badges or counts shown after the title. */
  meta?: React.ReactNode;
  actions?: React.ReactNode;
  defaultOpen?: boolean;
  /** The institution boards' fold: a white card, a plain summary line and a body with no divider. */
  board?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  if (board) {
    return (
      <details className={boardCardClipped} open={defaultOpen}>
        <summary className="box-content min-h-[24px] cursor-pointer px-5 py-3.5 text-assess-label font-medium text-ink">
          {number !== undefined ? `${number}. ${title}` : title}
          {meta ? <span className="ml-2 inline-flex gap-1">{meta}</span> : null}
        </summary>
        <div className="px-5 pb-4 text-assess-label text-ink-muted">
          {description ? <p className="text-assess-meta text-ink-subtle">{description}</p> : null}
          {children}
        </div>
      </details>
    );
  }
  return (
    <div className="overflow-hidden rounded-osce-md border border-border">
      <div className="flex flex-wrap items-center justify-between gap-2 bg-canvas px-4 py-2">
        <button
          type="button"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left text-osce-body font-semibold text-ink"
        >
          <HiOutlineChevronRight
            className={cn(
              "h-4 w-4 shrink-0 text-ink-subtle transition-transform",
              open && "rotate-90",
            )}
            aria-hidden
          />
          {number !== undefined ? (
            <Badge tone="neutral" size="xs">
              {number}
            </Badge>
          ) : null}
          <span className="truncate">{title}</span>
          {meta ? <span className="flex shrink-0 gap-1">{meta}</span> : null}
        </button>
        {actions ? <div className="flex shrink-0 items-center gap-1">{actions}</div> : null}
      </div>
      <div className={open ? "border-t border-border p-4" : "hidden"}>
        {description ? <p className="mb-3 text-osce-meta text-ink-subtle">{description}</p> : null}
        {children}
      </div>
    </div>
  );
}

/**
 * A titled surface. The console is a stack of these on every screen. A part
 * that folds is a `FoldSection`.
 */
export function Panel({
  title,
  description,
  actions,
  padding = "md",
  scrollable = true,
  className,
  bodyClassName,
  children,
}: {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  /** `"none"` for a panel whose body is its own full-bleed list (rows carry their own padding). */
  padding?: "none" | "sm" | "md";
  /** Off for a form whose in-flow dropdown would be cut off by the scroll cap. */
  scrollable?: boolean;
  className?: string;
  /** On the body, where `flex`/`gap` must go: `className` lands on the section, which only wraps the body. */
  bodyClassName?: string;
  children: React.ReactNode;
}) {
  const bodyPadding =
    padding === "none" ? "" : padding === "sm" ? "p-4" : "p-5 sm:p-6";
  return (
    <section
      className={cn(
        "rounded-osce-lg border border-border bg-surface",
        className,
      )}
    >
      {title ? (
        <header
          className={cn(
            "flex flex-wrap items-start justify-between gap-3 rounded-t-[inherit] bg-canvas px-5 py-3.5 sm:px-6",
            "border-b border-border",
          )}
        >
          <div className="min-w-0">
            <h2 className="font-heading text-osce-subheading font-semibold text-ink">
              {title}
            </h2>
            {description ? (
              <p className="mt-0.5 text-osce-meta text-ink-subtle">{description}</p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex shrink-0 items-center gap-2">{actions}</div>
          ) : null}
        </header>
      ) : null}
      <div className={cn(bodyPadding, scrollable && cardScrollBody, bodyClassName)}>
        {children}
      </div>
    </section>
  );
}

/** Cursor paging: the footer of a `padding="none"` panel's list, with the failure beside the button. */
export function LoadMore({
  hasMore,
  busy,
  onLoad,
  error,
}: {
  hasMore: boolean;
  busy: boolean;
  onLoad: () => void;
  error?: Error | null;
}) {
  if (!hasMore && !error) return null;
  return (
    <div className="flex flex-col items-center gap-2 border-t border-border px-5 py-3 sm:px-6">
      {error ? (
        <p className="text-osce-meta text-osce-danger-text">
          Could not load more: {error.message}
        </p>
      ) : null}
      {hasMore ? (
        <Button variant="secondary" size="sm" onClick={onLoad} disabled={busy}>
          {busy ? "Loading…" : error ? "Try again" : "Load more"}
        </Button>
      ) : null}
    </div>
  );
}

const STAT_COLUMNS = {
  4: "sm:grid-cols-2 lg:grid-cols-4",
  6: "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6",
} as const;

/** The assess dashboard's tile grid: `StatTile`s, four across from `lg` (six from `xl` for a wider set). */
export function StatGrid({
  children,
  label,
  columns = 4,
}: {
  children: React.ReactNode;
  /** Names the group for assistive technology. */
  label?: string;
  columns?: keyof typeof STAT_COLUMNS;
}) {
  return (
    <section aria-label={label} className={cn("grid grid-cols-1 gap-3", STAT_COLUMNS[columns])}>
      {children}
    </section>
  );
}

/** One count, drawn as the assess stat card; a tile with an `href` is a link. */
export function StatTile({
  label,
  value,
  href,
}: {
  label: string;
  value: number | string;
  href?: string;
}) {
  const body = (
    <>
      <span className={b2bTokens.b2bEyebrow}>{label}</span>
      <span className={b2bTokens.b2bStatCardValue}>{value}</span>
    </>
  );
  return href ? (
    <Link href={href} className={b2bTokens.b2bStatCard}>
      {body}
    </Link>
  ) : (
    <div className={b2bTokens.b2bStatCard}>{body}</div>
  );
}

/**
 * The console's empty state — the same one `AsyncBoundary` draws, so a list
 * that is empty looks identical whether the screen or the boundary noticed.
 */
export const EmptyPanel = EmptyState;

/**
 * A detail screen's two-column body — main facts left, a sticky action rail
 * right. Collapses to one column below `lg`, rail below main.
 */
export function DetailLayout({
  main,
  rail,
}: {
  main: React.ReactNode;
  rail?: React.ReactNode;
}) {
  if (!rail) return <div className="flex flex-col gap-6">{main}</div>;
  return (
    <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="flex min-w-0 flex-col gap-6">{main}</div>
      <div className="flex flex-col gap-6 lg:sticky lg:top-6">{rail}</div>
    </div>
  );
}

/** The rail's own panel — actions grouped, destructive ones last past a divider. */
export function ActionRail({
  title = "Actions",
  children,
  danger,
}: {
  title?: string;
  children: React.ReactNode;
  danger?: React.ReactNode;
}) {
  return (
    <FoldSection title={title}>
      <div className="flex flex-col gap-3">
        {children}
        {danger ? (
          <div className="flex flex-col gap-3 border-t border-border pt-3">
            {danger}
          </div>
        ) : null}
      </div>
    </FoldSection>
  );
}

/** A key/value definition grid for facts on a detail screen — two columns from `sm`, or one in a rail. */
const FACT_COLUMNS = {
  1: "",
  2: "sm:grid-cols-2",
  3: "sm:grid-cols-2 lg:grid-cols-3",
} as const;

export function FactList({
  items,
  columns = 2,
}: {
  items: { label: string; value: React.ReactNode }[];
  columns?: 1 | 2 | 3;
}) {
  return (
    <dl
className={cn("grid gap-x-6 gap-y-4", FACT_COLUMNS[columns])}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-osce-caption font-semibold uppercase tracking-wide text-ink-subtle">
            {item.label}
          </dt>
          <dd className="mt-0.5 truncate text-osce-data text-ink">
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
