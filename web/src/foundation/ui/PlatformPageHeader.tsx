"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { HiOutlineChevronLeft } from "react-icons/hi2";

/**
 * Staff console page title.
 *
 * Deliberately its own layout, not `B2CPageHeader`: the consumer header bands
 * the title under a bottom border and gives its icon top billing, sized for a
 * screen someone lands on once. A console screen is read over and over, so
 * the title sits inline with the body — no band — and the primary action is
 * what a scanning eye needs, on the right.
 */
export function PlatformPageHeader({
  title,
  description,
  actions,
  back,
}: {
  title: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
  /** A link back to the listing this screen drilled in from. */
  back?: { href: string; label?: string };
}) {
  return (
    <div>
      {back ? (
        <Link
          href={back.href}
          className="mb-3 inline-flex items-center gap-1 text-osce-meta font-medium text-ink-subtle transition-colors hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent/20"
        >
          <HiOutlineChevronLeft className="h-4 w-4" aria-hidden />
          {back.label ?? "Back"}
        </Link>
      ) : null}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <div className="min-w-0">
            <h1 className="truncate text-osce-title font-medium text-ink">
              {title}
            </h1>
            {description ? (
              <p className="mt-1 max-w-prose text-osce-meta leading-relaxed text-ink-subtle">
                {description}
              </p>
            ) : null}
          </div>
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </div>
  );
}
