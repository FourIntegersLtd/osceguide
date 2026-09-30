"use client";

import Link from "next/link";
import type { IconType } from "react-icons";
import { HiOutlineChevronRight } from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";
import { Button } from "@/foundation/ui/Button";

/**
 * Staff console layout primitives.
 *
 * The console used to borrow the consumer B2C card chrome directly — a bare
 * title floating over a `Card`, cramped rows, one long column on a detail
 * screen. This is the console's own kit: panels with the header inside them,
 * a KPI grid, a sticky action rail on detail screens. Tokens only
 * (`text-osce-*`, `osce-*`/`b2c-*` colours) — no raw sizes, no black.
 */

/** A titled surface. The console is a stack of these on every screen. */
export function Panel({
  title,
  description,
  actions,
  padding = "md",
  className,
  children,
}: {
  title?: string;
  description?: string;
  actions?: React.ReactNode;
  /** `"none"` for a panel whose body is its own full-bleed list (rows carry their own padding). */
  padding?: "none" | "sm" | "md";
  className?: string;
  children: React.ReactNode;
}) {
  const bodyPadding = padding === "none" ? "" : padding === "sm" ? "p-4" : "p-5 sm:p-6";
  return (
    <section
      className={cn(
        "rounded-osce-lg border border-b2c-border bg-osce-surface",
        className,
      )}
    >
      {title ? (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-b2c-border px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <h2 className="font-heading text-osce-subheading font-semibold text-osce-ink-900">
              {title}
            </h2>
            {description ? (
              <p className="mt-0.5 text-osce-meta text-b2c-text-muted">{description}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
        </header>
      ) : null}
      <div className={bodyPadding}>{children}</div>
    </section>
  );
}

/** A card holding a divided list. Every listing on the console is one. */
export function RowList({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("overflow-hidden rounded-osce-lg border border-b2c-border bg-osce-surface", className)}>
      <ul className="divide-y divide-b2c-border">{children}</ul>
    </div>
  );
}

export function Row({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <li className={cn("flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 sm:px-6", className)}>
      {children}
    </li>
  );
}

/** A `Row` that is a whole link — the destination pattern (directories, "go to"). */
export function RowLink({
  href,
  title,
  subtitle,
  icon: Icon,
  trailing,
}: {
  href: string;
  title: string;
  subtitle?: string;
  icon?: IconType;
  trailing?: React.ReactNode;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-b2c-surface-muted sm:px-6"
      >
        {Icon ? <Icon className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden /> : null}
        <span className="min-w-0 flex-1">
          <span className="block truncate text-osce-data font-medium text-osce-ink-900">{title}</span>
          {subtitle ? (
            <span className="block truncate text-osce-meta text-b2c-text-muted">{subtitle}</span>
          ) : null}
        </span>
        {trailing}
        <HiOutlineChevronRight className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
      </Link>
    </li>
  );
}

/** Cursor paging, as the one button every listing here uses. */
export function LoadMore({
  cursor,
  busy,
  onLoad,
}: {
  cursor: string | null | undefined;
  busy: boolean;
  onLoad: () => void;
}) {
  if (!cursor) return null;
  return (
    <div className="flex justify-center">
      <Button variant="secondary" size="sm" onClick={onLoad} disabled={busy}>
        {busy ? "Loading…" : "Load more"}
      </Button>
    </div>
  );
}

/** A 2/4-up grid of `StatTile`. */
export function StatGrid({ children }: { children: React.ReactNode }) {
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{children}</div>;
}

export function StatTile({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: IconType;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-osce-lg border border-b2c-border bg-osce-surface p-4">
      <div className="min-w-0">
        <p className="text-osce-caption font-semibold uppercase tracking-wide text-b2c-text-muted">
          {label}
        </p>
        <p className="mt-1 truncate font-heading text-osce-heading font-semibold tabular-nums text-osce-ink-900">
          {value}
        </p>
      </div>
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md bg-osce-accent-subtle text-osce-accent">
        <Icon className="h-4 w-4" aria-hidden />
      </span>
    </div>
  );
}

/** A dashed empty state, sized to sit where a `RowList` or `Table` would. */
export function EmptyPanel({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-osce-lg border border-dashed border-b2c-border px-6 py-10 text-center">
      <p className="text-osce-data font-semibold text-osce-ink-900">{title}</p>
      {description ? <p className="max-w-sm text-osce-meta text-b2c-text-muted">{description}</p> : null}
      {action}
    </div>
  );
}

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
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
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
    <Panel title={title} padding="sm">
      <div className="flex flex-col gap-3">
        {children}
        {danger ? (
          <div className="flex flex-col gap-3 border-t border-b2c-border pt-3">{danger}</div>
        ) : null}
      </div>
    </Panel>
  );
}

/** A key/value definition grid, two columns from `sm`, for facts on a detail screen. */
export function FactList({ items }: { items: { label: string; value: React.ReactNode }[] }) {
  return (
    <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-osce-caption font-semibold uppercase tracking-wide text-b2c-text-muted">
            {item.label}
          </dt>
          <dd className="mt-0.5 truncate text-osce-data text-osce-ink-900">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
