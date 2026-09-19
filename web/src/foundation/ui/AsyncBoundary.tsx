"use client";

import type { ReactNode } from "react";
import { Alert } from "@/foundation/ui/Alert";
import { Button } from "@/foundation/ui/Button";
import { EmptyState } from "@/foundation/ui/EmptyState";
import { Spinner } from "@/foundation/ui/Spinner";

export interface AsyncBoundaryProps<T> {
  state: { data: T | null; error: Error | null; loading: boolean; reload: () => void };
  /** Shown instead of `children` when the loader returned nothing worth rendering. */
  empty?: { title: ReactNode; description?: ReactNode; action?: ReactNode };
  /** Decides emptiness. Defaults to an empty array or a null result. */
  isEmpty?: (data: T) => boolean;
  children: (data: T) => ReactNode;
}

function defaultIsEmpty(data: unknown): boolean {
  return Array.isArray(data) ? data.length === 0 : data === null || data === undefined;
}

/**
 * Loading, failed and empty rendered the same way everywhere.
 *
 * Three states that look alike if each screen writes its own, which is how a
 * failure came to read as "nothing here". Keeping them in one component also
 * means a retry always exists on a failure, because there is nowhere to forget
 * to add one.
 */
export function AsyncBoundary<T>({ state, empty, isEmpty, children }: AsyncBoundaryProps<T>) {
  const { data, error, loading, reload } = state;

  if (loading && data === null) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (error) {
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
    return <EmptyState title={empty.title} description={empty.description} action={empty.action} />;
  }

  return <>{children(data)}</>;
}

function errorText(error: Error): string {
  return error.message || "Something went wrong.";
}
