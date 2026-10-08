"use client";

import type { ReactNode } from "react";
import { AsyncBoundary, Back, LoadingSpinner, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatLongDateTime } from "@/foundation/format";
import { readReferralHistory, type ReferralHistoryRow } from "@/capabilities/account/api";
import { StatusPill, settingsSub } from "@/capabilities/account/settings/SettingsKit";

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

/** One fact in a card's definition list: the term muted, the value in ink. */
function Fact({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-ink-muted">{label}</dt>
      <dd className="min-w-0 break-words text-ink">{children}</dd>
    </>
  );
}

const FACTS = "grid grid-cols-[max-content_1fr] gap-x-7 gap-y-2.5 text-osce-body";

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
    <div className="mx-auto w-full max-w-[1100px] space-y-4">
      <Back />
      <Panel title="Referral">
        <p className={settingsSub}>Referral not found.</p>
      </Panel>
    </div>
  );
}

function ReferralCards({ referral }: { referral: ReferralHistoryRow }) {
  return (
    <div className="mx-auto w-full max-w-[1100px] space-y-6">
      <div className="space-y-2">
        <Back />
        <h1 className="font-title text-osce-heading font-semibold text-ink">Referral</h1>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Panel title="Core information">
          <dl className={FACTS}>
            <Fact label="Date created">{formatLongDateTime(referral.redeemed_at)}</Fact>
            <Fact label="Code used">{referral.code}</Fact>
          </dl>
        </Panel>

        <Panel title="Financials &amp; payout">
          <dl className={FACTS}>
            <Fact label="Amount earned">{`£${(referral.earned_pence / 100).toFixed(2)}`}</Fact>
            <Fact label="Payout status">
              <StatusPill tone={referral.payout_status === "paid" ? "ok" : "warning"}>
                <span className="capitalize">{referral.payout_status}</span>
              </StatusPill>
            </Fact>
            <Fact label="Subscription">{(referral.plan_code ?? "").replace("_", " ")}</Fact>
          </dl>
        </Panel>

        <Panel title="Referee details">
          <dl className={FACTS}>
            <Fact label="Email">{referral.referee_email}</Fact>
          </dl>
        </Panel>
      </div>
    </div>
  );
}
