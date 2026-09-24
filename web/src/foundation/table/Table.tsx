"use client";

import { HiOutlineMagnifyingGlass, HiOutlineTrash, HiOutlineXMark } from "react-icons/hi2";
import React, { Fragment, useState, useEffect, useCallback, type ReactNode } from "react";
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
import { getInputClassName } from "@/foundation/ui/inputStyles";
import { errorMessage as getErrorMessage } from "@/foundation/hooks";
import { B2CErrorState } from "@/foundation/ui/B2CErrorState";
import { EmptyState } from "@/foundation/ui/EmptyState";

export interface FetchPageParams {
  page: number;
  perPage: number;
  cursor?: string | null;
  search: string;
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
  sortable?: boolean;
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

interface TablePropsBase<T> {
  columns: Column<T>[];
  idField: keyof T;
  nameField: keyof T;
  searchPlaceholder?: string;
  deletable?: boolean;
  onDelete?: (id: string, name: string) => void;
  linkBuilder?: (item: T) => string;
  /** In fetchPage mode, called with current page ids; in controlled mode, called with no args */
  onSelectAll?: (currentPageIds?: string[]) => void;
  selectedItems?: Set<string>;
  /** Optional section heading above the table */
  title?: ReactNode;
  /** Optional helper text under the title */
  description?: ReactNode;
  className?: string;
  /** When false, hides the search field (default true). */
  showSearch?: boolean;
  /**
   * Parent-owned search (e.g. `AuthoringCatalogFilterBar`). When `onSearchChange` is set,
   * the built-in search row is hidden unless `showSearch` is explicitly true.
   */
  search?: string;
  onSearchChange?: (value: string) => void;
  /** When false, hides pagination controls (default true). */
  showPagination?: boolean;
  /** Initial page size in fetchPage mode (default 10). */
  defaultItemsPerPage?: number;
  /** Optional second row under a data row (e.g. expander content). */
  renderExpandedRow?: (item: T) => ReactNode;
  isRowExpanded?: (item: T) => boolean;
  /** Whole-row click (e.g. toggle expander). Link/button cells should stop propagation. */
  onRowActivate?: (item: T) => void;
  /** Shown when a fetch or controlled load returns no rows. */
  empty?: {
    title: ReactNode;
    description?: ReactNode;
    action?: ReactNode;
  };
}

/** When fetchPage is provided, Table owns all pagination state and logic. Parent just provides the fetch. */
interface TablePropsWithFetch<T> extends TablePropsBase<T> {
  fetchPage: (params: FetchPageParams) => Promise<FetchPageResult<T>>;
  data?: never;
  totalItems?: never;
  currentPage?: never;
  itemsPerPage?: never;
  onPageChange?: never;
  onItemsPerPageChange?: never;
  onSearch?: never;
  loading?: never;
  cursorMode?: never;
  hasMore?: never;
}

/** When fetchPage is not provided, parent controls data and pagination (controlled mode). */
interface TablePropsControlled<T> extends TablePropsBase<T> {
  fetchPage?: never;
  data: T[];
  totalItems: number;
  currentPage: number;
  itemsPerPage: number;
  onPageChange: (page: number) => void;
  onItemsPerPageChange: (count: number) => void;
  onSearch: (query: string) => void;
  loading?: boolean;
  cursorMode?: boolean;
  hasMore?: boolean;
}

type TableProps<T> = TablePropsWithFetch<T> | TablePropsControlled<T>;

function isFetchPageMode<T>(
  props: TableProps<T>,
): props is TablePropsWithFetch<T> {
  return typeof (props as TablePropsWithFetch<T>).fetchPage === "function";
}

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

/** Shared search form used by both controlled and fetchPage tables. */
function TableSearchForm({
  searchQuery,
  searchPlaceholder,
  onSubmit,
  onClear,
  onInputChange,
}: {
  searchQuery: string;
  searchPlaceholder: string;
  onSubmit: (e: React.FormEvent) => void;
  onClear: () => void;
  onInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <div className="flex w-full justify-end">
      <form onSubmit={onSubmit} className="relative w-full max-w-md" role="search">
        <HiOutlineMagnifyingGlass
          className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-b2c-text-muted"
          aria-hidden
        />
        <input
          type="search"
          placeholder={searchPlaceholder}
          className={cn(
            getInputClassName(),
            "appearance-none pl-10 pr-24 [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden",
          )}
          value={searchQuery}
          onChange={onInputChange}
        />
        <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1.5">
          {searchQuery ? (
            <>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  onClear();
                }}
                className="rounded-md p-1.5 text-b2c-text-muted transition-colors hover:bg-b2c-surface-muted hover:text-b2c-text-secondary"
                type="button"
                aria-label="Clear search"
              >
                <HiOutlineXMark className="h-3.5 w-3.5" />
              </button>
              <Button type="submit" variant="primary" size="sm" themeType="b2c">
                Search
              </Button>
            </>
          ) : null}
        </div>
      </form>
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
  nameField,
  onDelete,
  renderExpandedRow,
  isRowExpanded,
  onRowActivate,
}: {
  data: T[];
  columns: Column<T>[];
  idField: keyof T;
  nameField: keyof T;
  onDelete?: (id: string, name: string) => void;
  renderExpandedRow?: (item: T) => ReactNode;
  isRowExpanded?: (item: T) => boolean;
  onRowActivate?: (item: T) => void;
}) {
  const primary =
    columns.find((column) => column.priority === "primary") ?? columns[0];
  const rows = columns.filter(
    (column) => column !== primary && column.priority !== "detail",
  );

  return (
    <div className="space-y-3 md:hidden">
      {data.map((item, index) => (
        <div
          key={rowKey(item, idField, index)}
          className={cn(
            b2cCard,
            "min-w-0 p-4",
            onRowActivate && "cursor-pointer",
          )}
          onClick={onRowActivate ? () => onRowActivate(item) : undefined}
          onKeyDown={
            onRowActivate
              ? (event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onRowActivate(item);
                  }
                }
              : undefined
          }
          role={onRowActivate ? "button" : undefined}
          tabIndex={onRowActivate ? 0 : undefined}
        >
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

          {onDelete ? (
            <div className="mt-3 flex justify-end border-t border-b2c-border pt-3">
              <button
                type="button"
                onClick={() =>
                  onDelete(String(item[idField]), String(item[nameField]))
                }
                className="inline-flex h-11 items-center gap-2 px-2 text-osce-body text-b2c-text-muted hover:text-osce-danger"
              >
                <HiOutlineTrash className="h-4 w-4" />
                Delete
              </button>
            </div>
          ) : null}

          {renderExpandedRow && isRowExpanded?.(item) ? (
            <div
              className="mt-3 border-t border-b2c-border pt-3"
              onClick={(event) => event.stopPropagation()}
            >
              {renderExpandedRow(item)}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}

/** Shared table grid (thead + tbody) used by both modes. */
function TableGrid<T extends object>({
  data,
  columns,
  idField,
  nameField,
  onDelete,
  onSelectAll,
  selectedItems,
  onSelectAllArg,
  renderExpandedRow,
  isRowExpanded,
  onRowActivate,
}: {
  data: T[];
  columns: Column<T>[];
  idField: keyof T;
  nameField: keyof T;
  onDelete?: (id: string, name: string) => void;
  onSelectAll?: (currentPageIds?: string[]) => void;
  selectedItems?: Set<string>;
  /** When set, onSelectAll is called with this (e.g. data.map id) for fetchPage mode */
  onSelectAllArg?: string[];
  renderExpandedRow?: (item: T) => ReactNode;
  isRowExpanded?: (item: T) => boolean;
  onRowActivate?: (item: T) => void;
}) {
  const colSpan = columns.length + (onDelete ? 1 : 0);

  return (
    <>
      <TableCards
        data={data}
        columns={columns}
        idField={idField}
        nameField={nameField}
        onDelete={onDelete}
        renderExpandedRow={renderExpandedRow}
        isRowExpanded={isRowExpanded}
        onRowActivate={onRowActivate}
      />

      <div
        className={cn(
          "hidden rounded-md border border-b2c-border md:block",
          b2cTableScroll,
        )}
      >
      <table
        data-b2c-table=""
        className="min-w-[900px] w-full divide-y divide-b2c-border"
      >
        <thead className="bg-b2c-surface-muted">
          <tr>
            {columns.map((column, index) => (
              <th
                key={index}
                className={`px-4 py-3 text-left ${b2cTableHeader} ${column.className || ""}`}
              >
                {index === 0 && onSelectAll ? (
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded-osce-sm border-osce-border text-osce-accent focus:ring-2 focus:ring-osce-accent-subtle"
                      checked={
                        !!(
                          selectedItems &&
                          selectedItems.size === data.length &&
                          data.length > 0
                        )
                      }
                      onChange={() =>
                        onSelectAll?.(onSelectAllArg ?? undefined)
                      }
                    />
                    {column.header}
                  </div>
                ) : (
                  column.header
                )}
              </th>
            ))}
            {onDelete ? (
              <th className={`px-4 py-3 text-right ${b2cTableHeader}`}>
                Actions
              </th>
            ) : null}
          </tr>
        </thead>
        <tbody className="divide-y divide-b2c-border bg-osce-surface">
          {data.map((item, index) => {
            const expanded = Boolean(
              renderExpandedRow && isRowExpanded?.(item),
            );
            return (
              <Fragment key={rowKey(item, idField, index)}>
                <tr
                  className={cn(
                    "transition-colors hover:bg-b2c-surface-muted",
                    onRowActivate && "cursor-pointer",
                  )}
                  onClick={
                    onRowActivate ? () => onRowActivate(item) : undefined
                  }
                >
                  {columns.map((column, colIndex) => (
                    <td
                      key={colIndex}
                      className={cn("whitespace-nowrap px-4 py-3", b2cTableCell)}
                    >
                      {renderCell(column, item)}
                    </td>
                  ))}
                  {onDelete ? (
                    <td className={cn("px-4 py-3 text-right", b2cTableCell)}>
                      <button
                        type="button"
                        onClick={() =>
                          onDelete(
                            String(item[idField]),
                            String(item[nameField]),
                          )
                        }
                        className="text-b2c-text-muted hover:text-osce-danger"
                        aria-label="Delete"
                      >
                        <HiOutlineTrash className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  ) : null}
                </tr>
                {expanded ? (
                  <tr>
                    <td
                      colSpan={colSpan}
                      className="bg-b2c-surface-muted px-4 py-3"
                      onClick={(event) => event.stopPropagation()}
                    >
                      {renderExpandedRow?.(item)}
                    </td>
                  </tr>
                ) : null}
              </Fragment>
            );
          })}
        </tbody>
      </table>
      </div>
    </>
  );
}

function TableInner<T extends object>(props: TableProps<T>) {
  const {
    columns,
    idField,
    nameField,
    searchPlaceholder = "Search...",
    onDelete,
    onSelectAll,
    selectedItems,
    title,
    description,
    className = "",
    showSearch = true,
    showPagination = true,
    renderExpandedRow,
    isRowExpanded,
    onRowActivate,
    empty,
    search: controlledSearch,
    onSearchChange,
  } = props;

  const searchExternallyOwned = controlledSearch !== undefined;
  const [internalSearchQuery, setInternalSearchQuery] = useState("");
  const searchQuery = searchExternallyOwned ? controlledSearch : internalSearchQuery;
  const setSearchQuery = onSearchChange ?? setInternalSearchQuery;
  const effectiveShowSearch = searchExternallyOwned ? showSearch === true : showSearch;

  if (isFetchPageMode(props)) {
    return (
      <TableWithPagination
        {...props}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        searchPlaceholder={searchPlaceholder}
        showSearch={effectiveShowSearch}
        showPagination={showPagination}
        empty={empty}
      />
    );
  }

  const {
    data,
    totalItems,
    currentPage,
    itemsPerPage,
    onPageChange,
    onItemsPerPageChange,
    onSearch,
    loading = false,
    cursorMode = false,
    hasMore = false,
  } = props;

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    onSearch("");
  };

  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setSearchQuery(newValue);
    if (newValue === "") onSearch("");
  };

  return (
    <TableShell title={title} description={description} className={className}>
      {effectiveShowSearch ? (
        <TableSearchForm
          searchQuery={searchQuery}
          searchPlaceholder={searchPlaceholder}
          onSubmit={handleSearch}
          onClear={handleClearSearch}
          onInputChange={handleSearchInputChange}
        />
      ) : null}
      {loading ? (
        <div className="py-4 text-center" role="status">
          <span className="text-osce-body text-b2c-text-secondary">Loading…</span>
        </div>
      ) : null}
      {!loading && data.length === 0 && empty ? (
        <EmptyState title={empty.title} description={empty.description} action={empty.action} />
      ) : (
        <TableGrid<T>
          data={data}
          columns={columns}
          idField={idField}
          nameField={nameField}
          onDelete={onDelete}
          onSelectAll={onSelectAll}
          selectedItems={selectedItems}
          onSelectAllArg={data.map((item) => String(item[idField]))}
          renderExpandedRow={renderExpandedRow}
          isRowExpanded={isRowExpanded}
          onRowActivate={onRowActivate}
        />
      )}
      {showPagination && data.length > 0 ? (
        <Pagination
          currentPage={currentPage}
          totalItems={totalItems}
          itemsPerPage={itemsPerPage}
          onPageChange={onPageChange}
          onItemsPerPageChange={onItemsPerPageChange}
          cursorMode={cursorMode}
          hasMore={hasMore}
        />
      ) : null}
    </TableShell>
  );
}

/** Table with internal pagination: owns state, calls fetchPage when page/search/perPage change. */
function TableWithPagination<T extends object>(
  props: TablePropsWithFetch<T> & {
    searchQuery: string;
    setSearchQuery: (q: string) => void;
    searchPlaceholder: string;
    showSearch: boolean;
    showPagination: boolean;
    empty?: TablePropsBase<T>["empty"];
  },
) {
  const {
    fetchPage,
    columns,
    idField,
    nameField,
    searchPlaceholder,
    onDelete,
    onSelectAll,
    selectedItems,
    searchQuery,
    setSearchQuery,
    title,
    description,
    className = "",
    showSearch,
    showPagination,
    defaultItemsPerPage = 10,
    renderExpandedRow,
    isRowExpanded,
    onRowActivate,
    empty,
  } = props;

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
  const [loading, setLoading] = useState(false);
  const [searchVersion, setSearchVersion] = useState(0);

  const loadPage = useCallback(
    async (
      page: number,
      perPage: number,
      search: string,
      cursor: string | null,
    ) => {
      setLoading(true);
      setFetchError(null);
      try {
        const result = await fetchPage({ page, perPage, cursor, search });
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
        console.error("fetchPage failed:", err);
        setData([]);
        setTotalItems(0);
        setHasMore(false);
        setHasKnownTotalFromApi(false);
        setFetchError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    },
    [fetchPage],
  );

  useEffect(() => {
    setCurrentPage(1);
    setCursorForPage({ 1: null });
  }, [searchQuery, itemsPerPage, fetchPage]);

  useEffect(() => {
    const cursor =
      currentPage === 1 ? null : (cursorForPage[currentPage] ?? null);
    loadPage(currentPage, itemsPerPage, searchQuery, cursor);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- cursorForPage intentionally omitted to avoid refetch loops
  }, [
    currentPage,
    itemsPerPage,
    searchQuery,
    fetchPage,
    searchVersion,
    loadPage,
  ]);

  const handlePageChange = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  const handleItemsPerPageChange = useCallback((perPage: number) => {
    setItemsPerPage(perPage);
    setCurrentPage(1);
    setCursorForPage({ 1: null });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPage(1);
    setCursorForPage({ 1: null });
    setSearchVersion((v) => v + 1);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setCurrentPage(1);
    setCursorForPage({ 1: null });
  };

  const handleSearchInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    setSearchQuery(newValue);
    if (newValue === "") {
      setCurrentPage(1);
      setCursorForPage({ 1: null });
    }
  };

  const displayTotalItems =
    totalItems > 0
      ? totalItems
      : (currentPage - 1) * itemsPerPage + data.length;

  return (
    <TableShell title={title} description={description} className={className}>
      {showSearch ? (
        <TableSearchForm
          searchQuery={searchQuery}
          searchPlaceholder={searchPlaceholder}
          onSubmit={handleSearch}
          onClear={handleClearSearch}
          onInputChange={handleSearchInputChange}
        />
      ) : null}
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
              searchQuery,
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
          nameField={nameField}
          onDelete={onDelete}
          onSelectAll={onSelectAll}
          selectedItems={selectedItems}
          onSelectAllArg={data.map((item) => String(item[idField]))}
          renderExpandedRow={renderExpandedRow}
          isRowExpanded={isRowExpanded}
          onRowActivate={onRowActivate}
        />
      )}
      {showPagination && data.length > 0 ? (
        <Pagination
          currentPage={currentPage}
          totalItems={displayTotalItems}
          itemsPerPage={itemsPerPage}
          onPageChange={handlePageChange}
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
  return <TableInner<T> {...props} />;
}

export default Table;
