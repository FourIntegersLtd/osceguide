"use client";

import React, { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Pagination from "@/foundation/ui/Pagination";
import {
  b2cCard,
  b2cFieldLabel,
  b2cFieldValue,
  b2cSectionTitle,
  b2cTableCell,
  b2cTableHeader,
  b2cTableScroll,
} from "@/foundation/ui/productTokens";
import {
  ModalHelper,
} from "@/foundation/ui/ModalContent";
import { Button } from "@/foundation/ui/Button";
import { cn } from "@/foundation/ui/cn";
import { errorMessage as getErrorMessage } from "@/foundation/hooks";
import { B2CErrorState } from "@/foundation/ui/B2CErrorState";
import { EmptyState } from "@/foundation/ui/EmptyState";

export interface FetchPageParams {
  page: number;
  perPage: number;
  cursor?: string | null;
}

export interface FetchPageResult<T> {
  items: T[];
  totalCount?: number;
  nextCursor?: string | null;
  hasMore?: boolean;
}

/** One column. Exported so a screen can name its column list rather than
 * infer it, which is how the retiring client's screens declared them. */
export interface Column<T> {
  header: string;
  key: keyof T | ((item: T) => React.ReactNode);
  render?: (item: T) => React.ReactNode;
  /** On the header and every cell of the column, so `hidden lg:table-cell` hides both. */
  className?: string;
  /**
   * How this column behaves in the stacked card layout used below `md`.
   * "primary" is the card heading (the first column if none is marked),
   * "secondary" is a label/value row, and "detail" is dropped entirely —
   * use it for columns that only earn their space on a wide screen.
   * Defaults to "secondary".
   */
  priority?: "primary" | "secondary" | "detail";
}

/**
 * The "Load more" footer of a `rows` table. The shape `useCursorPages`
 * returns, so a screen passes its pages straight through: `more={pages}`.
 */
export interface TableMore {
  hasMore: boolean;
  loadingMore: boolean;
  moreError: Error | null;
  loadMore: () => void;
}

interface TablePropsBase<T> {
  columns: Column<T>[];
  idField: keyof T;
  /** Optional section heading above the table */
  title?: ReactNode;
  /** Optional helper text under the title */
  description?: ReactNode;
  className?: string;
  /**
   * Drops the table's own border, for a table that is the body of a panel
   * which already has one.
   */
  bare?: boolean;
  /** The narrowest the grid gets before it scrolls sideways (default `min-w-[900px]`). */
  minWidthClassName?: string;
  /** The skin of the table's own buttons. */
  themeType?: React.ComponentProps<typeof Button>["themeType"];
  /** Shown instead of the grid when there are no rows. */
  empty?: {
    title: ReactNode;
    description?: ReactNode;
    action?: ReactNode;
  };
}

/**
 * The screen read the rows (one server page at a time, through
 * `useCursorPages`) and the table draws them. It does not re-page, re-sort or
 * re-filter what it is given; `more` adds the footer that asks for the next
 * server page.
 */
interface TablePropsWithRows<T> extends TablePropsBase<T> {
  rows: T[];
  more?: TableMore;
  fetchPage?: never;
  defaultItemsPerPage?: never;
}

/**
 * The table owns the paging: it calls `fetchPage` as the page or the page size
 * changes and draws a numbered pager. For a list whose total is known.
 */
interface TablePropsWithFetch<T> extends TablePropsBase<T> {
  fetchPage: (params: FetchPageParams) => Promise<FetchPageResult<T>>;
  /** Initial page size (default 10). */
  defaultItemsPerPage?: number;
  rows?: never;
  more?: never;
}

type TableProps<T> = TablePropsWithRows<T> | TablePropsWithFetch<T>;

function TableShell({
  title,
  description,
  className = "",
  children,
}: {
  title?: ReactNode;
  description?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("min-w-0 max-w-full space-y-4", className)}>
      {title || description ? (
        <div className="space-y-1">
          {title ? (
            <h2 className={b2cSectionTitle}>
              {title}
            </h2>
          ) : null}
          {description ? (
            <ModalHelper className="mt-0">{description}</ModalHelper>
          ) : null}
        </div>
      ) : null}
      {children}
    </div>
  );
}

/** Resolve a column's content for one row — same rules in table and card mode. */
function renderCell<T extends object>(
  column: Column<T>,
  item: T,
): React.ReactNode {
  if (column.render) return column.render(item);
  if (typeof column.key === "function") return column.key(item);
  return String(item[column.key]);
}

function rowKey<T>(item: T, idField: keyof T, index: number) {
  const idVal = item[idField];
  return idVal != null && idVal !== "" ? String(idVal) : `row-${index}`;
}

/**
 * Below `md` the table becomes a list of cards. A 900px grid on a 390px
 * screen is a horizontal scroll nobody discovers — the app hides scrollbars
 * globally, so there is nothing on screen to suggest the row continues.
 * Columns opt into their role here via `Column.priority`.
 */
function TableCards<T extends object>({
  data,
  columns,
  idField,
  bare,
}: {
  data: T[];
  columns: Column<T>[];
  idField: keyof T;
  bare: boolean;
}) {
  const primary =
    columns.find((column) => column.priority === "primary") ?? columns[0];
  const rows = columns.filter(
    (column) => column !== primary && column.priority !== "detail",
  );

  return (
    <div className={cn("space-y-3 md:hidden", bare && "p-4")}>
      {data.map((item, index) => (
        <div key={rowKey(item, idField, index)} className={cn(b2cCard, "min-w-0 p-4")}>
          {primary ? (
            <div className={cn("min-w-0 break-words", b2cFieldValue)}>
              {renderCell(primary, item)}
            </div>
          ) : null}

          {rows.length > 0 ? (
            <dl className="mt-3 space-y-2">
              {rows.map((column, colIndex) => (
                <div
                  key={colIndex}
                  className="flex items-start justify-between gap-3"
                >
                  <dt className={cn("shrink-0", b2cFieldLabel)}>
                    {column.header}
                  </dt>
                  <dd
                    className={cn(
                      "min-w-0 break-words text-right",
                      b2cTableCell,
                    )}
                  >
                    {renderCell(column, item)}
                  </dd>
                </div>
              ))}
            </dl>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/** The grid (thead + tbody) from `md` up, and the cards below it. */
function TableGrid<T extends object>({
  data,
  columns,
  idField,
  bare,
  minWidthClassName,
}: {
  data: T[];
  columns: Column<T>[];
  idField: keyof T;
  bare: boolean;
  minWidthClassName: string;
}) {
  return (
    <>
      <TableCards data={data} columns={columns} idField={idField} bare={bare} />

      <div
        className={cn(
          "hidden md:block",
          !bare && "rounded-md border border-b2c-border",
          b2cTableScroll,
        )}
      >
        <table
          data-b2c-table=""
          className={cn("w-full divide-y divide-b2c-border", minWidthClassName)}
        >
          <thead className="bg-b2c-surface-muted">
            <tr>
              {columns.map((column, index) => (
                <th
                  key={index}
                  scope="col"
                  className={cn("px-4 py-3 text-left", b2cTableHeader, column.className)}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-b2c-border bg-osce-surface">
            {data.map((item, index) => (
              <tr
                key={rowKey(item, idField, index)}
                className="transition-colors hover:bg-b2c-surface-muted"
              >
                {columns.map((column, colIndex) => (
                  <td
                    key={colIndex}
                    className={cn("whitespace-nowrap px-4 py-3", b2cTableCell, column.className)}
                  >
                    {renderCell(column, item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/** Rows the screen already holds, with the "Load more" footer when the server has more. */
function TableWithRows<T extends object>({
  rows,
  more,
  columns,
  idField,
  title,
  description,
  className,
  bare = false,
  minWidthClassName = "min-w-[900px]",
  themeType,
  empty,
}: TablePropsWithRows<T>) {
  return (
    <TableShell title={title} description={description} className={className}>
      {rows.length === 0 && empty ? (
        <EmptyState title={empty.title} description={empty.description} action={empty.action} />
      ) : (
        <TableGrid<T>
          data={rows}
          columns={columns}
          idField={idField}
          bare={bare}
          minWidthClassName={minWidthClassName}
        />
      )}
      {more && (more.hasMore || more.moreError) ? (
        <div className={cn("flex flex-col items-center gap-2", bare && "px-4 pb-4")}>
          {more.moreError ? (
            <p className="text-osce-meta text-osce-danger-text" role="alert">
              Could not load more: {more.moreError.message}
            </p>
          ) : null}
          {more.hasMore ? (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              themeType={themeType}
              disabled={more.loadingMore}
              onClick={more.loadMore}
            >
              {more.loadingMore ? "Loading…" : more.moreError ? "Try again" : "Load more"}
            </Button>
          ) : null}
        </div>
      ) : null}
    </TableShell>
  );
}

/** Table with internal pagination: owns state, calls fetchPage when page/perPage change. */
function TableWithPagination<T extends object>({
  fetchPage,
  columns,
  idField,
  title,
  description,
  className,
  bare = false,
  minWidthClassName = "min-w-[900px]",
  defaultItemsPerPage = 10,
  empty,
}: TablePropsWithFetch<T>) {
  const [data, setData] = useState<T[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(defaultItemsPerPage);
  const [totalItems, setTotalItems] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isCursorMode, setIsCursorMode] = useState(false);
  const [hasKnownTotalFromApi, setHasKnownTotalFromApi] = useState(false);
  const [cursorForPage, setCursorForPage] = useState<
    Record<number, string | null>
  >({ 1: null });
  // True from the first render, so an empty state is never drawn before the first answer.
  const [loading, setLoading] = useState(true);
  // The newest request. An answer to an older one (a filter changed, a page
  // was skipped past) is dropped rather than drawn over the newer rows.
  const latestRequest = useRef(0);

  const loadPage = useCallback(
    async (page: number, perPage: number, cursor: string | null) => {
      const request = (latestRequest.current += 1);
      setLoading(true);
      setFetchError(null);
      try {
        const result = await fetchPage({ page, perPage, cursor });
        if (request !== latestRequest.current) return;
        setData(result.items ?? []);
        if (result.totalCount != null) {
          setTotalItems(result.totalCount);
          setHasKnownTotalFromApi(true);
        } else {
          setTotalItems((page - 1) * perPage + (result.items?.length ?? 0));
          setHasKnownTotalFromApi(false);
        }
        if (result.nextCursor !== undefined && result.hasMore !== undefined) {
          setHasMore(result.hasMore ?? false);
          setIsCursorMode(result.totalCount == null);
          if (result.hasMore && result.nextCursor != null) {
            setCursorForPage((prev) => ({
              ...prev,
              [page + 1]: result.nextCursor!,
            }));
          }
        } else {
          setHasMore(false);
          setIsCursorMode(false);
        }
      } catch (err) {
        if (request !== latestRequest.current) return;
        console.error("fetchPage failed:", err);
        setData([]);
        setTotalItems(0);
        setHasMore(false);
        setHasKnownTotalFromApi(false);
        setFetchError(getErrorMessage(err));
      } finally {
        if (request === latestRequest.current) setLoading(false);
      }
    },
    [fetchPage],
  );

  useEffect(() => {
    setCurrentPage(1);
    setCursorForPage({ 1: null });
  }, [itemsPerPage, fetchPage]);

  useEffect(() => {
    const cursor =
      currentPage === 1 ? null : (cursorForPage[currentPage] ?? null);
    void loadPage(currentPage, itemsPerPage, cursor);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- cursorForPage intentionally omitted to avoid refetch loops
  }, [currentPage, itemsPerPage, loadPage]);

  const handleItemsPerPageChange = useCallback((perPage: number) => {
    setItemsPerPage(perPage);
    setCurrentPage(1);
    setCursorForPage({ 1: null });
  }, []);

  const displayTotalItems =
    totalItems > 0
      ? totalItems
      : (currentPage - 1) * itemsPerPage + data.length;

  return (
    <TableShell title={title} description={description} className={className}>
      {loading ? (
        <div className="py-4 text-center" role="status">
          <span className="text-osce-body text-b2c-text-secondary">Loading…</span>
        </div>
      ) : null}
      {!loading && fetchError ? (
        <B2CErrorState
          variant="plain"
          title="We couldn't load these rows"
          description={fetchError}
          onRetry={() =>
            void loadPage(
              currentPage,
              itemsPerPage,
              currentPage === 1 ? null : (cursorForPage[currentPage] ?? null),
            )
          }
        />
      ) : null}
      {!loading && !fetchError && data.length === 0 && empty ? (
        <EmptyState title={empty.title} description={empty.description} action={empty.action} />
      ) : (
        <TableGrid<T>
          data={data}
          columns={columns}
          idField={idField}
          bare={bare}
          minWidthClassName={minWidthClassName}
        />
      )}
      {data.length > 0 ? (
        <Pagination
          currentPage={currentPage}
          totalItems={displayTotalItems}
          itemsPerPage={itemsPerPage}
          onPageChange={setCurrentPage}
          onItemsPerPageChange={handleItemsPerPageChange}
          cursorMode={isCursorMode}
          hasMore={hasMore}
          knownTotal={hasKnownTotalFromApi}
        />
      ) : null}
    </TableShell>
  );
}

function Table<T extends object>(props: TableProps<T>) {
  return typeof props.fetchPage === "function" ? (
    <TableWithPagination<T> {...props} />
  ) : (
    <TableWithRows<T> {...(props as TablePropsWithRows<T>)} />
  );
}

export default Table;
