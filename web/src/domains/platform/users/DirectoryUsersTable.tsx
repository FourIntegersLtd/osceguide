"use client";

import Link from "next/link";
import { useCallback, useMemo, type ReactNode } from "react";
import { LuChevronRight, LuShieldCheck } from "react-icons/lu";
import Table, {
  type FetchPageParams,
  type FetchPageResult,
} from "@/foundation/table/Table";
import { Badge } from "@/foundation/ui";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  readDirectory,
  type DirectoryFilters,
  type DirectoryUser,
} from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";
import {
  accessLabel,
  accessOf,
  accessTone,
  planLabel,
  userStatusTone,
} from "@/domains/platform/users/vocabulary";

/**
 * One exam group's slice of the account directory, cursor-paged on the server.
 *
 * Filters live in `DirectoryFilters` above the page; this table does not
 * duplicate the search box.
 */
export function DirectoryUsersTable({
  filters,
  hrefFor,
  totalCount,
  empty,
}: {
  filters: DirectoryFilters;
  hrefFor: (path: string) => string;
  /** From `directory/summary` when the active filters match a summary bucket. */
  totalCount?: number;
  empty: {
    title: string;
    description?: string;
    action?: ReactNode;
  };
}) {
  const fetchPage = useCallback(
    async (params: FetchPageParams,
    ): Promise<FetchPageResult<DirectoryUser>> => {
      const page = await readDirectory({
        ...filters,
        limit: params.perPage,
        cursor: params.cursor ?? undefined,
        q: filters.q?.trim() || undefined,
      });
      return {
        items: page.items,
        totalCount,
        nextCursor: page.next_cursor ?? null,
        hasMore: Boolean(page.next_cursor),
      };
    },
    [filters, totalCount],
  );

  const columns = useMemo(
    () => [
      {
        header: "Account",
        key: "email" as keyof DirectoryUser,
        priority: "primary" as const,
        render: (user: DirectoryUser) => (
          <div className="min-w-0">
            <Link
              href={hrefFor(`/users/${user.id}`)}
              className={cn(b2cTableCellText, "font-medium text-ink hover:text-accent")}
            >
              {user.email}
            </Link>
            <p className={cn("mt-0.5 truncate text-osce-meta text-ink-subtle", b2cTableCellText,
              )}>
              {user.name || "No name"} · joined {formatDay(user.created_at)}
              {user.last_login_at
                ? ` · last signed in ${formatDay(user.last_login_at)}`
                : " · never signed in"}
              {user.attempt_count > 0
                ? ` · ${user.attempt_count} attempt${user.attempt_count === 1 ? "" : "s"}`
                : ""}
            </p>
          </div>
        ),
      },
      {
        header: "Access",
        key: "has_paid" as keyof DirectoryUser,
        className: "hidden lg:table-cell",
        priority: "secondary" as const,
        render: (user: DirectoryUser) => {
          const access = accessOf(user);
          return (
            <div className="flex flex-wrap items-center gap-1.5">
              {user.is_platform_admin ? (
                <Badge tone="accent">
                  <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                  Console
                </Badge>
              ) : null}
              <Badge tone={user.signed_in ? "success" : "neutral"}>
                {user.signed_in ? "Session open" : "No open session"}
              </Badge>
              <Badge tone={accessTone(access)}>{accessLabel(access)}</Badge>
              {user.has_paid ? (
                <Badge tone="info">{planLabel(user.plan_code)}</Badge>
              ) : null}
              <Badge tone={userStatusTone(user.status)}>
                {user.status === "deactivated" ? "Deactivated" : "Active"}
              </Badge>
            </div>
          );
        },
      },
      {
        header: "",
        key: "id" as keyof DirectoryUser,
        priority: "detail" as const,
        className: "w-10",
        render: (user: DirectoryUser) => (
          <Link
            href={hrefFor(`/users/${user.id}`)}
            className="inline-flex text-ink-subtle hover:text-accent"
            aria-label={`Open ${user.email}`}
          >
            <LuChevronRight className="h-4 w-4" aria-hidden />
          </Link>
        ),
      },
    ],
    [hrefFor],
  );

  return (
    <Table<DirectoryUser>
      fetchPage={fetchPage}
      columns={columns}
      idField="id"
      defaultItemsPerPage={10}
      empty={empty}
    />
  );
}
