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
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  Back,
  LoadingSpinner,
  ModalHelper,
  ModalTitle,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import { readReferralHistory, type ReferralHistoryRow } from "@/capabilities/account/api";

function DetailRow({ icon, label, value }: { icon: ReactNode; label: string; value: ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0 text-b2c-text-muted">{icon}</span>
      <div className="min-w-0">
        <p className="text-osce-caption font-medium text-b2c-text-muted">{label}</p>
        <p className="text-osce-body font-medium text-osce-ink-900">{value}</p>
      </div>
    </div>
  );
}

/** The old `formatDate`: "26 September 2026 at 18:44". */
function formatDate(iso: string | null | undefined): string {
  if (!iso) return "No date provided";
  const date = new Date(iso);
  if (!Number.isFinite(date.getTime())) return "Invalid date";
  return date.toLocaleDateString("en-GB", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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
      referral: (await readReferralHistory(signal)).find((row) => row.id === referralId) ?? null,
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
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>Referral details</B2CPanelCardHeader>
        <B2CPanelCardBody>
          <ModalHelper className="mt-0">Referral not found.</ModalHelper>
        </B2CPanelCardBody>
      </B2CPanelCard>
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
        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Core information</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
            <div>
              <ModalTitle className="text-osce-body">Referral details</ModalTitle>
              <ModalHelper>When this referral was created and how.</ModalHelper>
            </div>
            <DetailRow
              icon={<HiOutlineCalendarDays className="h-4 w-4" />}
              label="Date created"
              value={formatDate(referral.redeemed_at)}
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
          </B2CPanelCardBody>
        </B2CPanelCard>

        <B2CPanelCard className="mt-0">
          <B2CPanelCardHeader>Financials &amp; payout</B2CPanelCardHeader>
          <B2CPanelCardBody className="space-y-4">
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
          </B2CPanelCardBody>
        </B2CPanelCard>

        <B2CPanelCard className="mt-0 md:col-span-2">
          <B2CPanelCardHeader>Referee details</B2CPanelCardHeader>
          <B2CPanelCardBody>
            <DetailRow
              icon={<HiOutlineEnvelope className="h-4 w-4" />}
              label="Referee email"
              value={referral.referee_email}
            />
          </B2CPanelCardBody>
        </B2CPanelCard>
      </div>
    </div>
  );
}
