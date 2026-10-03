"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { HiInformationCircle } from "react-icons/hi";
import { HiOutlineArrowPath, HiOutlineMagnifyingGlass } from "react-icons/hi2";
import Table, { type Column, type FetchPageResult } from "@/foundation/table/Table";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  Button,
  ButtonLink,
  productTokens,
  iconSearchInputClassName,
} from "@/foundation/ui";
import { errorMessage, useCursorPages, useToast, useSearchQuery } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { flagSetEntry, listFlaggedStations, type FlaggedEntry } from "@/domains/train/api";
import { flaggedEntryPath } from "@/domains/train/mocks/model";
import { B2CHero } from "@/foundation/ui/B2CHero";

const PAGE_LIMIT = 25;

/** A row is the flagged entry, with the title the backend resolved for it. */
type FlagRow = FlaggedEntry & { id: string; station_name: string };

/**
 * The stations this person flagged to come back to, each in its own session.
 *
 * The retiring client read `user.flagged_stations` — an array on the learner's
 * own document — and resolved each title by listing every station it could
 * fetch and matching on id, which is why a case off that page printed "Unknown
 * Station". A flag is a mark on a practice set's entry now, so the title and
 * the session arrive with it, and a row reopens the station inside the session
 * it was flagged in rather than the library's copy.
 *
 * It is the same list the runner's flag button writes to, which is the point of
 * the tab. Reporting a station as wrong is a different button and goes to the
 * content team, not here.
 *
 * A page at a time, searched in SQL: this used to load the whole flag list and
 * filter it by title in the browser.
 */
export function FlaggedStations() {
  const { hrefFor } = useSurface();
  const toast = useToast();

  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);
  const pages = useCursorPages(
    (cursor, signal) =>
      listFlaggedStations({ cursor, limit: PAGE_LIMIT, search: query || null }, signal),
    [query],
  );
  const flags = pages.state;

  const [removing, setRemoving] = useState<string | null>(null);

  const unflag = async (row: FlagRow) => {
    setRemoving(row.id);
    try {
      await flagSetEntry(row.set_id, row.entry_id, false);
      flags.reload();
    } catch (cause) {
      toast.show({ tone: "error", title: "We couldn't remove the flag", message: errorMessage(cause) });
    } finally {
      setRemoving(null);
    }
  };

  const rows = useMemo<FlagRow[]>(
    () =>
      (flags.data ?? []).map((flag) => ({
        ...flag,
        id: flag.entry_id,
        station_name: flag.station_title ?? "Unknown Station",
      })),
    [flags.data],
  );

  // Every row loaded so far, with the table's own pager off: paging is the
  // server's cursor (Load more), and filtering already happened in SQL.
  const fetchPage = useCallback(
    async (): Promise<FetchPageResult<FlagRow>> => ({ items: rows, totalCount: rows.length }),
    [rows],
  );

  if (flags.loading) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Flagged stations</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <div className="flex items-center justify-center py-8">
            <HiOutlineArrowPath className="h-8 w-8 animate-spin text-osce-accent" aria-hidden />
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  if (flags.error) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Flagged stations</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <p className="text-osce-body text-b2c-text-secondary">
            {errorMessage(flags.error)} We could not read what you have reported. Try again in a
            moment.
          </p>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  if (rows.length === 0 && !query) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Flagged stations</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <div className="flex items-start gap-3 rounded-md border border-b2c-border bg-b2c-surface-muted p-3 sm:p-4">
            <HiInformationCircle className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent" aria-hidden />
            <p className={productTokens.b2cBodyText}>
              Flag a station during a mock to see it here for quick review.
            </p>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  const columns: Column<FlagRow>[] = [
    {
      header: "Station",
      key: "station_name",
      render: (row) => (
        <Link href={hrefFor(flaggedEntryPath(row))} className={productTokens.b2cLink}>
          {row.station_name}
        </Link>
      ),
    },
    {
      header: "Session",
      key: "set_name",
    },
    {
      header: "Action",
      key: (row) => (
        <span className="flex flex-wrap items-center gap-3">
          <Link href={hrefFor(flaggedEntryPath(row))} className={productTokens.b2cLink}>
            Open
          </Link>
          <button
            type="button"
            className={productTokens.b2cLink}
            disabled={removing !== null}
            onClick={() => void unflag(row)}
          >
            {removing === row.id ? "Removing…" : "Remove flag"}
          </button>
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <B2CHero
        eyebrow="Flagged stations"
        title="Stations to come back to"
        action={
          <ButtonLink href="?tab=combine" variant="primary" size="md">
            Combine into a session
          </ButtonLink>
        }
      >
        Stations you flagged during practice. Open one to review it, or combine them into a new session.
      </B2CHero>
      <div>
        <label className="relative block w-full max-w-md">
          <span className="sr-only">Search flagged stations</span>
          <HiOutlineMagnifyingGlass
            className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-b2c-text-muted"
            aria-hidden
          />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search flagged stations"
            className={iconSearchInputClassName}
          />
        </label>
      </div>
      <Table<FlagRow>
        className="mb-4"
        fetchPage={fetchPage}
        showPagination={false}
        columns={columns}
        idField="id"
        nameField="station_name"
        deletable={false}
        showSearch={false}
      />
      {pages.moreError ? (
        <Alert tone="danger">Could not load more: {pages.moreError.message}</Alert>
      ) : null}
      {pages.hasMore ? (
        <div className="mb-24 flex justify-center">
          <Button variant="secondary" size="sm" disabled={pages.loadingMore} onClick={pages.loadMore}>
            {pages.loadingMore ? "Loading…" : "Load more"}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
