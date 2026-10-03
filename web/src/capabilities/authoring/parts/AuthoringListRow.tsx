"use client";

import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

/**
 * One catalogue row: identity on the left, status + icon actions on the right.
 */
export function AuthoringListRow({
  title,
  meta,
  metaTitle,
  detail,
  leading,
  onOpen,
  children,
}: {
  title: string;
  meta?: string;
  metaTitle?: string;
  detail?: ReactNode;
  leading?: ReactNode;
  onOpen?: () => void;
  children: ReactNode;
}) {
  const chrome = useAuthoringChrome();
  const identity = (
    <>
      <p className={cn("truncate text-osce-meta font-medium", chrome.headline)}>{title}</p>
      {meta ? (
        <p
          className={cn("mt-0.5 truncate text-osce-caption", chrome.bodyMuted)}
          title={metaTitle}
        >
          {meta}
        </p>
      ) : null}
      {detail}
    </>
  );

  return (
    <div
      className={cn(
        "flex flex-col gap-3 px-4 py-2.5 sm:flex-row sm:items-center sm:px-5",
        chrome.rowHover,
      )}
    >
      {leading}
      {onOpen ? (
        <button
          type="button"
          onClick={onOpen}
          className="min-w-0 flex-1 rounded-osce-md text-left focus:outline-none focus:ring-2 focus:ring-osce-accent/20 focus:ring-offset-1"
        >
          {identity}
        </button>
      ) : (
        <div className="min-w-0 flex-1">{identity}</div>
      )}
      <div className="flex shrink-0 items-center gap-2">{children}</div>
    </div>
  );
}
