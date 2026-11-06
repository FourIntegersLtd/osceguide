"use client";

import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { boardActs, boardMeta } from "@/capabilities/authoring/parts/boardUi";
import { boardRowWide } from "@/foundation/ui/boardKit";
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
  linkTitle = false,
  children,
}: {
  title: string;
  meta?: string;
  metaTitle?: string;
  detail?: ReactNode;
  leading?: ReactNode;
  onOpen?: () => void;
  /** Organisation arms: the title is drawn as a link (the boards' blue). */
  linkTitle?: boolean;
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

  if (!chrome.b2c) {
    return (
      <div data-row className={boardRowWide}>
        <span className="min-w-0 flex-[1_1_260px]">
          {onOpen ? (
            <button
              type="button"
              onClick={onOpen}
              className={cn("p-0 text-left font-bold", linkTitle && "font-normal text-osce-accent hover:text-osce-accent-hover")}
            >
              {title}
            </button>
          ) : (
            <b>{title}</b>
          )}
          {meta ? (
            <div className={boardMeta} title={metaTitle}>
              {meta}
            </div>
          ) : null}
          {detail}
        </span>
        <div className={boardActs}>{children}</div>
      </div>
    );
  }

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
