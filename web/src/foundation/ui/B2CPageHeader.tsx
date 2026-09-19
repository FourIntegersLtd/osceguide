"use client";

import type { ElementType, ReactNode } from "react";
import Link from "next/link";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import { b2cPageHeaderShell, b2cPageHeaderTitle } from "@/foundation/ui/productTokens";

type BackProp = { href?: string; label?: string; onClick?: () => void };

export type B2CPageHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  icon?: ElementType<{ className?: string }>;
  variant?: "compact" | "hero";
  action?: ReactNode;
  back?: BackProp;
  className?: string;
  /**
   * @deprecated Shell already clears the fixed mobile nav via `b2cShellMain` Pt-16.
   * Kept for API compat; no longer adds extra top margin.
   */
  mobileNavOffset?: boolean;
};

/*
 * The retiring version guessed its icon by matching the current path against
 * the consumer nav table. That made a heading depend on a nav that only one
 * arm had, and it is why this component could not be used anywhere else.
 * Callers pass `icon` now, or get none.
 */

export function B2CPageHeader({
  eyebrow,
  title,
  subtitle,
  icon,
  variant = "compact",
  action,
  back,
  className = "",
  mobileNavOffset: _mobileNavOffset = true,
}: B2CPageHeaderProps) {
  void _mobileNavOffset;
  const HeaderIcon = icon ?? null;
  const backLabel = back?.label ?? "Back";
  const backContent = (
    <>
      <HiOutlineChevronLeft className="h-4 w-4" aria-hidden="true" />
      <span>{backLabel}</span>
    </>
  );
  const backLinkClasses =
    "inline-flex items-center gap-1 rounded-md text-osce-meta font-medium text-b2c-text-muted hover:text-osce-ink-900 focus:outline-none focus:ring-2 focus:ring-osce-accent/20";

  return (
    <div
      className={[b2cPageHeaderShell, className].filter(Boolean).join(" ")}
    >
      {back && (
        <div className="mb-3">
          {back.href ? (
            <Link href={back.href} className={backLinkClasses}>
              {backContent}
            </Link>
          ) : (
            <button
              type="button"
              onClick={back.onClick}
              className={backLinkClasses}
            >
              {backContent}
            </button>
          )}
        </div>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1 sm:pr-2">
          {eyebrow ? (
            <p className="mb-1.5 text-osce-meta font-medium text-b2c-text-muted">
              {eyebrow}
            </p>
          ) : null}
          <div className="flex items-center gap-3">
            {HeaderIcon ? (
              // `HeaderIcon` is the `icon` prop or a nav-table lookup, not a
              // component defined during render.
              // eslint-disable-next-line react-hooks/static-components
              <HeaderIcon
                className="h-7 w-7 shrink-0 text-osce-accent sm:h-8 sm:w-8"
                aria-hidden="true"
              />
            ) : null}
            <div className="min-w-0">
              <h1
                className={
                  variant === "hero"
                    ? "text-osce-heading font-semibold leading-tight tracking-tight text-osce-ink-900"
                    : b2cPageHeaderTitle
                }
              >
                {title}
              </h1>
              {subtitle && (
                <p
                  className={
                    variant === "hero"
                      ? "mt-1.5 max-w-2xl text-osce-body leading-relaxed text-b2c-text-muted"
                      : "mt-2 text-osce-meta leading-snug text-b2c-text-muted"
                  }
                >
                  {subtitle}
                </p>
              )}
            </div>
          </div>
        </div>
        {action ? (
          <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto sm:shrink-0 sm:justify-end">
            {action}
          </div>
        ) : null}
      </div>
    </div>
  );
}
