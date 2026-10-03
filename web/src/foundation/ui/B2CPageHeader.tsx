"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import {
  b2cMonoEyebrow,
  b2cPageHeaderShell,
  b2cPageHeaderTitle,
} from "@/foundation/ui/productTokens";

type BackProp = { href?: string; label?: string; onClick?: () => void };

export type B2CPageHeaderProps = {
  eyebrow?: ReactNode;
  /** Almost always a string; a screen with its own inline-rename control (the rubric builder) passes a node instead. */
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  back?: BackProp;
  className?: string;
};

/**
 * The page header from the canvas (`train-dashboard`): an eyebrow, the
 * Fraunces title, one muted line, and the page's actions bottom-aligned on
 * the right. No icon and no rule underneath: the title carries the page.
 */
export function B2CPageHeader({
  eyebrow,
  title,
  subtitle,
  action,
  back,
  className = "",
}: B2CPageHeaderProps) {
  const backLabel = back?.label ?? "Back";
  const backContent = (
    <>
      <HiOutlineChevronLeft className="h-4 w-4" aria-hidden="true" />
      <span>{backLabel}</span>
    </>
  );
  const backLinkClasses =
    "inline-flex items-center gap-1 rounded-osce-md text-osce-meta font-medium text-b2c-text-muted hover:text-osce-ink-900 focus:outline-none focus:ring-2 focus:ring-osce-accent/20";

  return (
    <header className={[b2cPageHeaderShell, className].filter(Boolean).join(" ")}>
      {back && (
        <div className="mb-3">
          {back.href ? (
            <Link href={back.href} className={backLinkClasses}>
              {backContent}
            </Link>
          ) : (
            <button type="button" onClick={back.onClick} className={backLinkClasses}>
              {backContent}
            </button>
          )}
        </div>
      )}
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between sm:gap-6">
        <div className="flex min-w-0 flex-1 flex-col gap-1.5">
          {eyebrow ? <p className={b2cMonoEyebrow}>{eyebrow}</p> : null}
          <h1 className={b2cPageHeaderTitle}>{title}</h1>
          {subtitle ? (
            <p className="max-w-[640px] text-osce-body text-b2c-text-muted">{subtitle}</p>
          ) : null}
        </div>
        {action ? (
          <div className="flex flex-wrap items-center gap-2 sm:shrink-0 sm:justify-end">
            {action}
          </div>
        ) : null}
      </div>
    </header>
  );
}
