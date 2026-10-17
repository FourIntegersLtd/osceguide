"use client";

import type { ReactNode } from "react";
import { Alert } from "@/foundation/ui/Alert";
import { Button } from "@/foundation/ui/Button";
import { EmptyState } from "@/foundation/ui/EmptyState";
import { Spinner } from "@/foundation/ui/Spinner";

export interface AsyncBoundaryProps<T> {
  state: {
    data: T | null;
    error: Error | null;
    loading: boolean;
    reload: () => void;
  };
  /** Shown instead of `children` when the loader returned nothing worth rendering. */
  empty?: {
    title: ReactNode;
    description?: ReactNode;
    action?: ReactNode;
    bare?: boolean;
  };
  /** Decides emptiness. Defaults to an empty array or a null result. */
  isEmpty?: (data: T) => boolean;
  /** Replaces the default spinner, for a screen whose loading state is part of its design. */
  loading?: ReactNode;
  /** Replaces the default failure panel. It is handed the retry, so a retry still always exists. */
  failure?: (error: Error, retry: () => void) => ReactNode;
  children: (data: T) => ReactNode;
}

function defaultIsEmpty(data: unknown): boolean {
  return Array.isArray(data)
    ? data.length === 0
    : data === null || data === undefined;
}

/**
 * Loading, failed and empty rendered the same way everywhere.
 *
 * Three states that look alike if each screen writes its own, which is how a
 * failure came to read as "nothing here". Keeping them in one component also
 * means a retry always exists on a failure, because there is nowhere to forget
 * to add one.
 */
export function AsyncBoundary<T>({
  state,
  empty,
  isEmpty,
  loading: loadingView,
  failure,
  children,
}: AsyncBoundaryProps<T>) {
  const { data, error, loading, reload } = state;

  if (loading && data === null) {
    if (loadingView !== undefined) return <>{loadingView}</>;
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    if (failure) return <>{failure(error, reload)}</>;
    return (
      <Alert tone="danger" title="That did not load">
        <p>{errorText(error)}</p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={reload}>
          Try again
        </Button>
      </Alert>
    );
  }

  if (data === null) return null;

  const decideEmpty = isEmpty ?? defaultIsEmpty;
  if (empty && decideEmpty(data)) {
    return (
      <EmptyState
        title={empty.title}
        description={empty.description}
        action={empty.action}
        bare={empty.bare}
      />
    );
  }

  return <>{children(data)}</>;
}

function errorText(error: Error): string {
  return error.message || "Something went wrong.";
}
