"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import * as b2bTokens from "@/foundation/ui/b2bTokens";
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
  /** Let the subtitle run the full width of the page (the institution boards' description). */
  wideSubtitle?: boolean;
  /** The institution boards' header: plain accent back link, 11px eyebrow, 16px description (assess screens built to a board). "tight" is a 12px gap under the back link instead of 24. */
  board?: boolean | "tight";
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
  wideSubtitle = false,
  board = false,
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
      {back && board ? (
        <div className={board === "tight" ? "mb-3 leading-[normal]" : "mb-6"}>
          {back.href ? (
            <Link href={back.href} className="text-assess-label text-b2b-accent hover:text-b2b-accent-hover">
              ‹ {backLabel}
            </Link>
          ) : (
            <button type="button" onClick={back.onClick} className="text-assess-label text-b2b-accent hover:text-b2b-accent-hover">
              ‹ {backLabel}
            </button>
          )}
        </div>
      ) : back ? (
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
      ) : null}
      <div className={`flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between ${board ? "sm:gap-4" : "sm:gap-6"}`}>
        <div className={`flex min-w-0 flex-col gap-1.5 ${board ? "flex-[0_1_auto]" : "flex-1"}`}>
          {eyebrow ? <p className={board ? b2bTokens.assessEyebrow : b2cMonoEyebrow}>{eyebrow}</p> : null}
          <h1 className={board ? `${b2cPageHeaderTitle} !leading-[normal]` : b2cPageHeaderTitle}>{title}</h1>
          {subtitle ? (
            <p className={`${wideSubtitle ? "" : "max-w-[640px] "}${board ? `${b2bTokens.assessDesc} leading-normal` : "text-osce-body text-b2c-text-muted"}`}>{subtitle}</p>
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
