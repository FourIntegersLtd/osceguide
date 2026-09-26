"use client";

import Link from "next/link";
import { useState } from "react";
import { HiInformationCircle } from "react-icons/hi";
import { HiOutlineArrowPath } from "react-icons/hi2";
import Table, { type Column } from "@/foundation/table/Table";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readReferralHistory, type ReferralHistoryRow } from "@/capabilities/account/api";

const DEFAULT_ITEMS_PER_PAGE = 10;

/** Where one referral's own page lives. */
export function referralDetailPath(referralId: string): string {
  return `/settings/referrals/${referralId}`;
}

/**
 * Everybody who joined with your code: the retiring client's "Referral history".
 *
 * The same four columns, search box and paging, over `/me/referrals/history`.
 * Loading and the empty state are the old card's; with rows it is the shared
 * table, searched and paged in the browser as the old one was.
 */
export default function ReferralHistory() {
  const state = useAsync((signal) => readReferralHistory(signal), []);

  if (state.loading && state.data === null) {
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

  return <AsyncBoundary state={state}>{(rows) => <ReferralHistoryTable rows={rows} />}</AsyncBoundary>;
}

function ReferralHistoryTable({ rows }: { rows: ReferralHistoryRow[] }) {
  const { hrefFor } = useSurface();
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(DEFAULT_ITEMS_PER_PAGE);

  const filteredHistory = rows.filter((row) =>
    row.referee_email.toLowerCase().includes(searchQuery.toLowerCase()),
  );
  const totalPages = Math.max(1, Math.ceil(filteredHistory.length / itemsPerPage) || 1);
  const safePage = Math.min(currentPage, totalPages);
  const pageStart = (safePage - 1) * itemsPerPage;
  const pageData = filteredHistory.slice(pageStart, pageStart + itemsPerPage);

  if (filteredHistory.length === 0 && !searchQuery) {
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
      className="mb-24"
      title="Referral history"
      description="Track referees, earnings, and payout status."
      data={pageData}
      columns={columns}
      totalItems={filteredHistory.length}
      idField="id"
      nameField="referee_email"
      searchPlaceholder="Search by referee email..."
      deletable={false}
      onSearch={(query) => {
        setSearchQuery(query);
        setCurrentPage(1);
      }}
      onPageChange={setCurrentPage}
      onItemsPerPageChange={(count) => {
        setItemsPerPage(count);
        setCurrentPage(1);
      }}
      currentPage={safePage}
      itemsPerPage={itemsPerPage}
      loading={false}
    />
  );
}
