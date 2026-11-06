"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { b2bTokens, cn } from "@/foundation/ui";
import { boardCardClipped, boardRow } from "@/foundation/ui/boardKit";

/**
 * The home boards' list card (Today, SupervisorHome, LiveBoard): a head with the section's name and one aside,
 * then rows. The board's `.card` > `.head` > `.row`, drawn once for the three screens.
 */
export function BoardSection({ title, aside, children, label }: { title: string; aside?: ReactNode; children: ReactNode; label?: string }) {
  return (
    <section aria-label={label ?? title} className={boardCardClipped}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-osce-border-light px-5 py-4">
        <h2 className="text-assess-section font-semibold text-osce-ink-900">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  );
}

/**
 * One row. The board's `.row:first-of-type` drops the top border of the first link only (the head is a div),
 * so a first row that is a link passes `first`.
 */
export function BoardRow({ href, first = false, children }: { href?: string; first?: boolean; children: ReactNode }) {
  const className = cn(boardRow, first && "border-t-0", href && "hover:bg-osce-surface-inset");
  return href ? (
    <Link href={href} className={className}>
      {children}
    </Link>
  ) : (
    <div className={className}>{children}</div>
  );
}

/** A row's title and its muted line. */
export function RowText({ title, meta }: { title: ReactNode; meta?: ReactNode }) {
  return (
    <div className="min-w-0 flex-[1_1_240px]">
      <div className="font-medium">{title}</div>
      {meta ? <div className={b2bTokens.assessMeta}>{meta}</div> : null}
    </div>
  );
}

/** The board's `›` at a link row's end. */
export function RowChevron() {
  return (
    <span aria-hidden className={b2bTokens.assessMeta}>
      ›
    </span>
  );
}
