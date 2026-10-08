"use client";

import { Button, QuietCard } from "@/foundation/ui";
import type { DirectoryFilters } from "@/domains/platform/api";
import { DirectoryUsersTable } from "@/domains/platform/users/DirectoryUsersTable";

/**
 * One exam's accounts, paged on their own.
 *
 * A group loads its own first page and carries its own pagination, so the
 * directory can show every exam at once without walking the whole table —
 * the retiring console had a page per exam and this is the same shape with
 * the pages side by side.
 */
export function UserGroup({
  title,
  description,
  filters,
  hrefFor,
  totalCount,
  onClear,
}: {
  title: string;
  description?: string;
  filters: DirectoryFilters;
  hrefFor: (path: string) => string;
  totalCount?: number;
  onClear?: () => void;
}) {
  const narrowed = Boolean(filters.q || filters.access || filters.status || filters.planCode);

  return (
    <QuietCard title={title} subtitle={description}>
      <DirectoryUsersTable
        filters={filters}
        hrefFor={hrefFor}
        totalCount={totalCount}
        empty={
          narrowed
            ? {
                title: "Nobody matches those filters",
                description: "Clear them to see everyone on this exam.",
                action: onClear ? (
                  <Button variant="secondary" size="sm" onClick={onClear}>
                    Clear the filters
                  </Button>
                ) : undefined,
              }
            : {
                title: "No accounts yet",
                description: "Nobody has chosen this exam or been granted it.",
              }
        }
      />
    </QuietCard>
  );
}
