"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { HiInformationCircle } from "react-icons/hi";
import { HiOutlineArrowPath } from "react-icons/hi2";
import Table, { type Column } from "@/foundation/table/Table";
import {
  Badge,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { practiseHref } from "@/capabilities/stations";
import { myStationFlags, type StationFlag } from "@/capabilities/stations/api";

const PER_PAGE = 10;

/** A row is the report, with the title the backend resolved for it. */
type FlagRow = StationFlag & { id: string; station_name: string };

/**
 * What this person has reported, and nothing else's.
 *
 * The retiring client read `user.flagged_stations` — an array on the learner's
 * own document — and resolved each title by listing every station it could
 * fetch and matching on id, which is why a case off that page printed "Unknown
 * Station". A report is a row about a station now, so the title arrives with it.
 *
 * It is the same list the runner's flag button writes to, which is the point of
 * the tab: a report you cannot find again is a report you stop making.
 */
export function FlaggedStations() {
  const { hrefFor } = useSurface();
  const flags = useAsync((signal) => myStationFlags(signal), []);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [perPage, setPerPage] = useState(PER_PAGE);

  const rows = useMemo<FlagRow[]>(
    () =>
      (flags.data ?? [])
        .map((flag) => ({ ...flag, station_name: flag.station_title ?? "Unknown Station" }))
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

  if (rows.length === 0) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Flagged stations</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <div className="flex items-start gap-3 rounded-md border border-b2c-border bg-b2c-surface-muted p-3 sm:p-4">
            <HiInformationCircle className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent" aria-hidden />
            <p className="text-osce-body text-b2c-text-secondary">
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
        <span className="inline-flex flex-wrap items-center gap-2">
          <Link
            href={practiseHref(hrefFor, row.station_id)}
            className="text-osce-accent hover:underline"
          >
            {row.station_name}
          </Link>
          {row.status === "resolved" ? <Badge tone="success">Reviewed</Badge> : null}
        </span>
      ),
    },
    {
      header: "Action",
      key: (row) => (
        <Link
          href={practiseHref(hrefFor, row.station_id)}
          className="text-osce-accent hover:underline"
        >
          View details
        </Link>
      ),
    },
  ];

  return (
    <Table<FlagRow>
      className="mb-24"
      title="Flagged stations"
      description="Stations you marked for review during practice."
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
