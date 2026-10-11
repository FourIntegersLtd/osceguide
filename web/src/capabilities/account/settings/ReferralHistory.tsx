"use client";

import Link from "next/link";
import { useState } from "react";
import { HiInformationCircle, HiOutlineArrowPath, HiOutlineMagnifyingGlass } from "react-icons/hi2";
import Table, { type Column, type TableMore } from "@/foundation/table/Table";
import {
  Panel,
} from "@/foundation/ui";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readReferralHistory, type ReferralHistoryRow } from "@/capabilities/account/api";

const PAGE_LIMIT = 25;

/** Where one referral's own page lives. */
export function referralDetailPath(referralId: string): string {
  return `/settings/referrals/${referralId}`;
}

/**
 * Everybody who joined with your code: the retiring client's "Referral history".
 *
 * The same four columns as the old card, now a server page at a time over
 * `/me/referrals/history`, searched by referee email in SQL. This used to
 * fetch up to 500 rows in one call and page and filter them in the browser.
 */
export default function ReferralHistory() {
  const [search, setSearch] = useState("");
  // What the server is asked for: the box, once typing pauses.
  const query = useSearchQuery(search);
  const pages = useCursorPages(
    (cursor, signal) =>
      readReferralHistory({ cursor, limit: PAGE_LIMIT, search: query || null }, signal),
    [query],
  );
  const rows = pages.state.data ?? [];

  if (pages.state.loading && pages.state.data === null) {
    return (
      <Panel title="Referral history" className="mb-24">
          <div className="flex items-center justify-center py-8">
            <HiOutlineArrowPath className="h-8 w-8 animate-spin text-osce-accent" />
          </div>
      </Panel>
    );
  }

  if (pages.state.error) {
    return (
      <Panel title="Referral history" className="mb-24">
          <p className="text-osce-body text-ink-muted">
            We could not read your referral history. Try again in a moment.
          </p>
      </Panel>
    );
  }

  if (rows.length === 0 && !query) {
    return (
      <Panel title="Referral history" className="mb-24">
          <div className="flex items-start gap-3 rounded-osce-md border border-border bg-canvas p-3 sm:p-4">
            <HiInformationCircle className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent" />
            <p className="text-osce-body text-ink-muted">
              You currently have no referral history. Share your code to start earning!
            </p>
          </div>
      </Panel>
    );
  }

  return (
    <>
      <div className="mb-4 flex justify-end">
        <label className="relative block w-full max-w-md">
          <span className="sr-only">Search by referee email</span>
          <HiOutlineMagnifyingGlass
            className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-subtle"
            aria-hidden
          />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by referee email..."
            className="w-full appearance-none rounded-osce-lg border border-border bg-canvas py-2.5 pl-10 pr-3 text-osce-body text-ink outline-none placeholder:text-ink-subtle focus:border-osce-accent focus:bg-osce-surface focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden"
          />
        </label>
      </div>
      <ReferralHistoryTable rows={rows} more={pages} />
    </>
  );
}

function ReferralHistoryTable({ rows, more }: { rows: ReferralHistoryRow[]; more: TableMore }) {
  const { hrefFor } = useSurface();

  const columns: Column<ReferralHistoryRow>[] = [
    {
      header: "Referee Email",
      key: "referee_email",
      render: (row) => (
        <Link
          href={hrefFor(referralDetailPath(row.id))}
          className="cursor-pointer text-ink hover:text-osce-accent-hover hover:underline"
        >
          {row.referee_email}
        </Link>
      ),
    },
    {
      header: "Date Joined",
      key: "redeemed_at",
      render: (row) => (
        <span>{row.redeemed_at ? new Date(row.redeemed_at).toLocaleDateString() : "-"}</span>
      ),
    },
    {
      header: "Amount Earned",
      key: "earned_pence",
      render: (row) => (
        <span className="font-medium text-osce-success-text">
          £{(row.earned_pence / 100).toFixed(2)}
        </span>
      ),
    },
    {
      header: "Payout Status",
      key: "payout_status",
      render: (row) => (
        <span
          className={`rounded-osce-md px-2.5 py-1 text-osce-caption font-medium capitalize ${
            row.payout_status === "paid"
              ? "bg-osce-success-bg text-osce-success-text"
              : row.payout_status === "unpaid"
                ? "bg-osce-warning-bg text-osce-warning-text"
                : "bg-surface-raised text-ink-muted"
          }`}
        >
          {row.payout_status}
        </span>
      ),
    },
  ];

  return (
    <Table<ReferralHistoryRow>
      className={more.hasMore ? "mb-24" : "mb-4"}
      title="Referral history"
      description="Track referees, earnings, and payout status"
      rows={rows}
      more={more}
      columns={columns}
      idField="id"
    />
  );
}
