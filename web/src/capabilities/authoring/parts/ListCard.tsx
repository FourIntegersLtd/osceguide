"use client";

import type { ReactNode } from "react";
import { Alert, B2CSkeleton, Button, EmptyState, Panel } from "@/foundation/ui";
import { cn } from "@/foundation/ui/cn";
import { READER_EMPTY_TEXT } from "@/capabilities/authoring/parts/CannotAuthor";
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
  empty: {
    title: string;
    description: string;
    sameForReaders?: boolean;
    action?: ReactNode;
  };
  children: ReactNode;
}) {
  const chrome = useAuthoringChrome();
  const canAuthor = useCanAuthor();

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
          <span className={`text-osce-caption ${chrome.iconMuted}`}>
            {meta}
          </span>
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
            description={
              canAuthor || empty.sameForReaders
                ? empty.description
                : READER_EMPTY_TEXT
            }
            action={empty.action}
          />
        </div>
      ) : (
        <div className={cn(`divide-y ${chrome.listDivide}`)}>{children}</div>
      )}
    </Panel>
  );
}
