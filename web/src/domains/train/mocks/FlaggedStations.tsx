"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { HiInformationCircle } from "react-icons/hi";
import { HiOutlineArrowPath } from "react-icons/hi2";
import Table, { type Column } from "@/foundation/table/Table";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { flagSetEntry, listFlaggedStations, type FlaggedEntry } from "@/domains/train/api";
import { flaggedEntryPath } from "@/domains/train/mocks/model";

const PER_PAGE = 10;

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
 */
export function FlaggedStations() {
  const { hrefFor } = useSurface();
  const toast = useToast();
  const flags = useAsync((signal) => listFlaggedStations(signal), []);
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
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(PER_PAGE);

  const rows = useMemo<FlagRow[]>(
    () =>
      (flags.data ?? [])
        .map((flag) => ({
          ...flag,
          id: flag.entry_id,
          station_name: flag.station_title ?? "Unknown Station",
        }))
        .filter((row) => row.station_name.toLowerCase().includes(search.toLowerCase())),
    [flags.data, search],
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

  if ((flags.data ?? []).length === 0) {
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

  const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
  const safePage = Math.min(page, totalPages);

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
    <Table<FlagRow>
      className="mb-24"
      title="Flagged stations"
      description="Stations you flagged during practice to come back to."
      data={rows.slice((safePage - 1) * perPage, safePage * perPage)}
      columns={columns}
      totalItems={rows.length}
      idField="id"
      nameField="station_name"
      searchPlaceholder="Search flagged stations..."
      deletable={false}
      onSearch={(query) => {
        setSearch(query);
        setPage(1);
      }}
      onPageChange={setPage}
      onItemsPerPageChange={(count) => {
        setPerPage(count);
        setPage(1);
      }}
      currentPage={safePage}
      itemsPerPage={perPage}
      loading={false}
    />
  );
}
