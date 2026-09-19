"use client";

import type { ReactNode } from "react";
import { Alert, B2CSkeleton, Button, Card, EmptyState } from "@/foundation/ui";

/**
 * A section's list: a header strip, an action error, and one of
 * loading / empty / rows.
 *
 * The three authoring trees each rendered this and each got the empty copy
 * slightly different. The copy is passed in; the frame is not.
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
  return (
    <Card themeType="b2b" padding="none" className="overflow-hidden">
      <div className="flex flex-col gap-1 border-b border-b2b-border px-4 pt-3 pb-2 sm:flex-row sm:items-center sm:justify-between sm:gap-2 sm:px-5">
        <span className="text-osce-caption font-medium uppercase tracking-wide text-b2b-mid">
          {countLabel} ({count})
        </span>
        {meta ? <span className="text-osce-caption text-b2b-icon">{meta}</span> : null}
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
        <div className="divide-y divide-b2b-border">{children}</div>
      )}
    </Card>
  );
}
