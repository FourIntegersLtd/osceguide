"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { HiInformationCircle, HiOutlineArrowPath, HiOutlineMagnifyingGlass } from "react-icons/hi2";
import Table, { type Column, type FetchPageResult } from "@/foundation/table/Table";
import {
  Alert,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  Button,
} from "@/foundation/ui";
import { useCursorPages } from "@/foundation/hooks";
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
  const [query, setQuery] = useState("");
  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const pages = useCursorPages(
    (cursor, signal) =>
      readReferralHistory({ cursor, limit: PAGE_LIMIT, search: query || null }, signal),
    [query],
  );
  const rows = pages.state.data ?? [];

  if (pages.state.loading && pages.state.data === null) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Referral history</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <div className="flex items-center justify-center py-8">
            <HiOutlineArrowPath className="h-8 w-8 animate-spin text-osce-accent" />
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  if (pages.state.error) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Referral history</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <p className="text-osce-body text-b2c-text-secondary">
            We could not read your referral history. Try again in a moment.
          </p>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  if (rows.length === 0 && !query) {
    return (
      <B2CPanelCard className="mt-0 mb-24">
        <B2CPanelCardHeader>Referral history</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <div className="flex items-start gap-3 rounded-md border border-b2c-border bg-b2c-surface-muted p-3 sm:p-4">
            <HiInformationCircle className="mt-0.5 h-5 w-5 shrink-0 text-osce-accent" />
            <p className="text-osce-body text-b2c-text-secondary">
              You currently have no referral history. Share your code to start earning!
            </p>
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>
    );
  }

  return (
    <>
      <div className="mb-4 flex justify-end">
        <label className="relative block w-full max-w-md">
          <span className="sr-only">Search by referee email</span>
          <HiOutlineMagnifyingGlass
            className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-b2c-text-muted"
            aria-hidden
          />
          <input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by referee email..."
            className="w-full appearance-none rounded-lg border border-b2c-border bg-b2c-surface-muted py-2.5 pl-10 pr-3 text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400 focus:border-osce-accent focus:bg-osce-surface focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden"
          />
        </label>
      </div>
      <ReferralHistoryTable rows={rows} />
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
    </>
  );
}

function ReferralHistoryTable({ rows }: { rows: ReferralHistoryRow[] }) {
  const { hrefFor } = useSurface();

  // Every row loaded so far, with the table's own pager off: paging is the
  // server's cursor (Load more), and filtering already happened in SQL.
  const fetchPage = useCallback(
    async (): Promise<FetchPageResult<ReferralHistoryRow>> => ({ items: rows, totalCount: rows.length }),
    [rows],
  );

  const columns: Column<ReferralHistoryRow>[] = [
    {
      header: "Referee Email",
      key: "referee_email",
      render: (row) => (
        <Link
          href={hrefFor(referralDetailPath(row.id))}
          className="cursor-pointer text-osce-ink-900 hover:text-osce-accent-hover hover:underline"
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
          className={`rounded-md px-2.5 py-1 text-osce-caption font-medium capitalize ${
            row.payout_status === "paid"
              ? "bg-osce-success-bg text-osce-success-text"
              : row.payout_status === "unpaid"
                ? "bg-osce-warning-bg text-osce-warning-text"
                : "bg-b2c-secondary text-b2c-text-secondary"
          }`}
        >
          {row.payout_status}
        </span>
      ),
    },
  ];

  return (
    <Table<ReferralHistoryRow>
      className="mb-4"
      title="Referral history"
      description="Track referees, earnings, and payout status."
      fetchPage={fetchPage}
      showPagination={false}
      columns={columns}
      idField="id"
      nameField="referee_email"
      deletable={false}
      showSearch={false}
    />
  );
}
