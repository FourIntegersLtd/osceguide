"use client";

import type { ReactNode } from "react";
import { Alert, B2CSkeleton, Button, EmptyState, Panel } from "@/foundation/ui";
import { cn } from "@/foundation/ui/cn";
import { READER_EMPTY_TEXT } from "@/capabilities/authoring/parts/CannotAuthor";
import { boardMeta } from "@/capabilities/authoring/parts/boardUi";
import { boardCardClipped, boardHeadRowWide, boardPadWide } from "@/foundation/ui/boardKit";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

/**
 * A section's list: a header strip, an action error, and one of
 * loading / empty / rows.
 */
export function ListCard({
  count,
  countLabel,
  meta,
  loading = false,
  error,
  onDismissError,
  empty,
  children,
}: {
  count: number;
  countLabel: string;
  meta?: ReactNode;
  loading?: boolean;
  error?: string | null;
  onDismissError?: () => void;
  /** `description` guides an author; a reader sees "Nothing here yet." unless `sameForReaders`. */
  empty: { title: string; description: string; sameForReaders?: boolean; action?: ReactNode };
  children: ReactNode;
}) {
  const chrome = useAuthoringChrome();
  const canAuthor = useCanAuthor();

  if (!chrome.b2c) {
    const emptyText = canAuthor || empty.sameForReaders ? empty.description : READER_EMPTY_TEXT;
    if (count === 0 && !loading && !error) {
      return (
        <div className={boardPadWide}>
          <h2 className="m-0 text-osce-body font-semibold !leading-[normal] text-ink">{empty.title}</h2>
          <p className={`m-0 ${boardMeta}`}>{emptyText}</p>
          {empty.action}
        </div>
      );
    }
    return (
      <div className={boardCardClipped}>
        <div className={boardHeadRowWide}>
          <span>
            {countLabel} {count}
          </span>
          {meta ? <span>{meta}</span> : null}
        </div>
        {error ? (
          <div className="border-t border-osce-border-light p-5">
            <Alert tone="danger">
              <div className="flex items-start justify-between gap-3">
                <p>{error}</p>
                {onDismissError ? (
                  <Button variant="ghost" size="xs" onClick={onDismissError}>
                    Dismiss
                  </Button>
                ) : null}
              </div>
            </Alert>
          </div>
        ) : null}
        {loading ? (
          <div className="border-t border-osce-border-light p-5">
            <B2CSkeleton lines={3} />
          </div>
        ) : (
          children
        )}
      </div>
    );
  }

  return (
    <Panel padding="none" className="overflow-hidden">
      <div
        className={cn(
          "flex flex-col gap-1 px-4 pt-3 pb-2 sm:flex-row sm:items-center sm:justify-between sm:gap-2 sm:px-5",
          `border-b ${chrome.listBorder}`,
        )}
      >
        <span className="text-osce-meta font-medium text-ink">
          {countLabel} <span className={chrome.captionMuted}>{count}</span>
        </span>
        {meta ? (
          <span className={`text-osce-caption ${chrome.iconMuted}`}>{meta}</span>
        ) : null}
      </div>
      {error ? (
        <div className="p-5">
          <Alert tone="danger">
            <div className="flex items-start justify-between gap-3">
              <p>{error}</p>
              {onDismissError ? (
                <Button variant="ghost" size="xs" onClick={onDismissError}>
                  Dismiss
                </Button>
              ) : null}
            </div>
          </Alert>
        </div>
      ) : null}
      {loading ? (
        <div className="p-5">
          <B2CSkeleton lines={3} />
        </div>
      ) : count === 0 ? (
        <div className="p-6">
          <EmptyState
            title={empty.title}
            description={canAuthor || empty.sameForReaders ? empty.description : READER_EMPTY_TEXT}
            action={empty.action}
          />
        </div>
      ) : (
        <div className={cn(`divide-y ${chrome.listDivide}`)}>{children}</div>
      )}
    </Panel>
  );
}
