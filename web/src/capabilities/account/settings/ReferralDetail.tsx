"use client";

import type { ReactNode } from "react";
import { LuHourglass } from "react-icons/lu";
import {
  HiOutlineBanknotes,
  HiOutlineCalendarDays,
  HiOutlineCheckCircle,
  HiOutlineCodeBracket,
  HiOutlineEnvelope,
  HiOutlineGift,
  HiOutlineTag,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  Back,
  LoadingSpinner,
  ModalHelper,
  ModalTitle,
  Panel,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { useCurrentExam } from "@/foundation/session";
import { readReferralHistory, type ReferralHistoryRow } from "@/capabilities/account/api";

/** The page cap `/me/referrals/history` uses per request. */
const HISTORY_PAGE_LIMIT = 100;
/** A bound on how many pages a single-referral lookup will walk. */
const MAX_LOOKUP_PAGES = 25;

/**
 * One referral by id, walking the history's cursor until found.
 *
 * There is no single-referral route, so this is a bounded lookup rather than
 * the list screen's server search — it stops at the first matching row
 * instead of reading every page to filter them, and gives up rather than
 * hanging on a referral history bigger than 2,500 rows.
 */
async function findReferral(
  referralId: string,
  signal: AbortSignal,
): Promise<ReferralHistoryRow | null> {
  let cursor: string | null = null;
  for (let page = 0; page < MAX_LOOKUP_PAGES; page += 1) {
    const result = await readReferralHistory({ cursor, limit: HISTORY_PAGE_LIMIT }, signal);
    const match = result.items.find((row) => row.id === referralId);
    if (match) return match;
    cursor = result.next_cursor ?? null;
    if (!cursor) break;
  }
  return null;
}

function DetailRow({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0 text-ink-subtle">{icon}</span>
      <div className="min-w-0">
        <p className="text-osce-caption font-medium text-ink-subtle">{label}</p>
        <p className="text-osce-body font-medium text-ink">{value}</p>
      </div>
    </div>
  );
}

function payoutStatusIcon(status: string): ReactNode {
  if (status === "paid") return <HiOutlineCheckCircle className="h-4 w-4 text-osce-success-icon" />;
  if (status === "unpaid") return <LuHourglass className="h-4 w-4 text-osce-warning-icon" />;
  return null;
}

/**
 * One referral: the retiring client's `ReferralDetail`, card for card.
 *
 * It is read from the same history list the table shows, since that list is
 * already the person's own rows and holds every field this page draws.
 */
export default function ReferralDetail({ referralId }: { referralId: string }) {
  const state = useAsync(
    async (signal) => ({
      referral: await findReferral(referralId, signal),
    }),
    [referralId],
  );

  if (state.loading && state.data === null) {
    return <LoadingSpinner showLabel label="Loading referral details..." />;
  }

  return (
    <AsyncBoundary state={state}>
      {({ referral }) => (referral ? <ReferralCards referral={referral} /> : <ReferralMissing />)}
    </AsyncBoundary>
  );
}

function ReferralMissing() {
  return (
    <div className="mx-auto max-w-4xl space-y-4 p-4">
      <Back />
      <Panel title="Referral details">
        <ModalHelper className="mt-0">Referral not found.</ModalHelper>
      </Panel>
    </div>
  );
}

function ReferralCards({ referral }: { referral: ReferralHistoryRow }) {
  // The old page printed the viewer's own app type here, not the referee's.
  const { code: examCode } = useCurrentExam();
  return (
    <div className="space-y-4">
      <Back />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Panel title="Core information">
          <div className="space-y-4">
            <div>
              <ModalTitle className="text-osce-body">Referral details</ModalTitle>
              <ModalHelper>When this referral was created and how.</ModalHelper>
            </div>
            <DetailRow
              icon={<HiOutlineCalendarDays className="h-4 w-4" />}
              label="Date created"
              value={formatLongDateTime(referral.redeemed_at)}
            />
            <DetailRow
              icon={<HiOutlineCodeBracket className="h-4 w-4" />}
              label="Referral code used"
              value={referral.code}
            />
            <DetailRow
              icon={<HiOutlineTag className="h-4 w-4" />}
              label="App type"
              value={examCode}
            />
          </div>
        </Panel>

        <Panel title="Financials &amp; payout">
          <div className="space-y-4">
            <DetailRow
              icon={<HiOutlineBanknotes className="h-4 w-4" />}
              label="Amount earned"
              value={`£${(referral.earned_pence / 100).toFixed(2)}`}
            />
            <DetailRow
              icon={payoutStatusIcon(referral.payout_status)}
              label="Payout status"
              value={<span className="capitalize">{referral.payout_status}</span>}
            />
            <DetailRow
              icon={<HiOutlineGift className="h-4 w-4" />}
              label="Subscription type (referee)"
              value={(referral.plan_code ?? "").replace("_", " ")}
            />
          </div>
        </Panel>

        <Panel title="Referee details" className="md:col-span-2">
          <DetailRow
            icon={<HiOutlineEnvelope className="h-4 w-4" />}
            label="Referee email"
            value={referral.referee_email}
          />
        </Panel>
      </div>
    </div>
  );
}
