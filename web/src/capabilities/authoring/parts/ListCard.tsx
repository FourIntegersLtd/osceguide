"use client";

import type { ReactNode } from "react";
import { Alert, B2CSkeleton, Button, EmptyState, Panel } from "@/foundation/ui";
import { cn } from "@/foundation/ui/cn";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

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
  empty: { title: string; description: string; action?: ReactNode };
  children: ReactNode;
}) {
  const chrome = useAuthoringChrome();

  return (
    <Panel padding="none" className="overflow-hidden">
      <div
        className={cn(
          "flex flex-col gap-1 px-4 pt-3 pb-2 sm:flex-row sm:items-center sm:justify-between sm:gap-2 sm:px-5",
          `border-b ${chrome.listBorder}`,
        )}
      >
        <span
          className={`text-osce-caption font-medium uppercase tracking-wide ${chrome.captionMuted}`}
        >
          {countLabel} ({count})
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
            description={empty.description}
            action={empty.action}
          />
        </div>
      ) : (
        <div className={cn(`divide-y ${chrome.listDivide}`)}>{children}</div>
      )}
    </Panel>
  );
}
