"use client";

import { useState } from "react";
import {
  Alert,
  AsyncBoundary,
  B2CGroupedRow,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  B2CSegmentedTabs,
  Badge,
  Button,
  ConfirmModal,
  Input,
  LoadMore,
  QuietCard,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync, useCursorPages } from "@/foundation/hooks";
import {
  listReferralPayouts,
  readOwedReferrals,
  setReferralPayout,
  type ReferralPayout,
} from "@/domains/platform/api";
import { formatMoney } from "@/foundation/format";
import { owedHeadline } from "@/domains/platform/payouts";
import { formatMoment } from "@/domains/platform/support";

type PayoutFilter = "unpaid" | "paid" | "all";

const FILTERS: B2CSegmentedTabItem<PayoutFilter>[] = [
  { id: "unpaid", label: "Owed" },
  { id: "paid", label: "Settled" },
  { id: "all", label: "Everything" },
];

type PayoutDetails = NonNullable<ReferralPayout["payout_details"]>;

/**
 * Where the transfer goes: the referrer's own bank details, decrypted for
 * staff only. Sort code and account number copy on a click, because they are
 * typed into a banking app next and a transposed digit sends money elsewhere.
 */
function PayTo({
  details,
  onCopyFailed,
}: {
  details: PayoutDetails;
  onCopyFailed: () => void;
}) {
  return (
    <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-osce-md bg-surface-raised px-3 py-2 text-osce-meta">
      <dt className="text-ink-subtle">Account holder</dt>
      <dd className="text-ink">{details.account_holder_name}</dd>
      <dt className="text-ink-subtle">Bank</dt>
      <dd className="text-ink">{details.bank_name}</dd>
      <dt className="text-ink-subtle">Sort code</dt>
      <dd>
        <CopyValue
          value={details.sort_code}
          label="sort code"
          onCopyFailed={onCopyFailed}
        />
      </dd>
      <dt className="text-ink-subtle">Account number</dt>
      <dd>
        <CopyValue
          value={details.account_number}
          label="account number"
          onCopyFailed={onCopyFailed}
        />
      </dd>
    </dl>
  );
}

function CopyValue({
  value,
  label,
  onCopyFailed,
}: {
  value: string;
  label: string;
  onCopyFailed: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      onCopyFailed();
    }
  };
  return (
    <span className="inline-flex items-center gap-2">
      <span className="select-all font-mono text-ink">{value}</span>
      <Button
        variant="ghost"
        size="sm"
        aria-label={`Copy ${label}`}
        onClick={() => copy()}
      >
        {copied ? "Copied" : "Copy"}
      </Button>
    </span>
  );
}

/** A redeemed referral whose referrer never saved bank details: nowhere to send it yet. */
function NoBankDetails() {
  return (
    <p className="mt-2 text-osce-meta text-ink-muted">
      No bank details saved. Ask the referrer to add them in Settings →
      Referrals.
    </p>
  );
}

/**
 * What we owe referrers, and what has been sent.
 *
 * Nothing on this screen moves money. Referrals are settled by a bank
 * transfer somebody makes by hand, so the only thing the product owes is an
 * honest record of whether that has happened — which is why marking a row is
 * reversible, and why a reference can be written against it.
 *
 * Owed first, because that is the list somebody is working through. A settled
 * row stays visible: "did we already pay this one?" is the question this
 * screen exists to answer, and a queue that hides the answer sends the money
 * twice.
 */
/** The opened referral: what to pay and where, or the settled record with its reversal. */
function SettleCard({
  referral,
  reference,
  busy,
  onReference,
  onRecord,
  onClose,
  onCopyFailed,
}: {
  referral: ReferralPayout;
  reference: string;
  busy: boolean;
  onReference: (value: string) => void;
  onRecord: (input: {
    payoutStatus: "paid" | "unpaid";
    payoutReference?: string | null;
  }) => void;
  onClose: () => void;
  onCopyFailed: () => void;
}) {
  const paid = referral.payout_status === "paid";
  const amount = `${formatMoney(referral.earned_pence)} to ${referral.referrer_email}`;
  return (
    <QuietCard
      title={paid ? `Settled ${amount}` : `Mark ${amount} as paid`}
      subtitle={`Referred ${referral.referred_email ?? "someone"}${
        referral.payout_reference
          ? ` · reference ${referral.payout_reference}`
          : ""
      }`}
      actions={
        paid ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => onRecord({ payoutStatus: "unpaid" })}
            >
              Not paid after all
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              Close
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="primary"
              size="sm"
              disabled={busy}
              onClick={() =>
                onRecord({
                  payoutStatus: "paid",
                  payoutReference: reference.trim() || null,
                })
              }
            >
              Record payment
            </Button>
            <Button variant="ghost" size="sm" disabled={busy} onClick={onClose}>
              Cancel
            </Button>
          </>
        )
      }
    >
      {paid ? null : (
        <>
          {referral.payout_details ? (
            <PayTo
              details={referral.payout_details}
              onCopyFailed={onCopyFailed}
            />
          ) : (
            <NoBankDetails />
          )}
          <Input
            label="Payment reference"
            value={reference}
            onChange={(event) => onReference(event.target.value)}
            placeholder="e.g. FT-2026-09-24"
            hint="The bank transfer reference, so you can match it on a statement later. Optional."
          />
        </>
      )}
    </QuietCard>
  );
}

export function ReferralPayouts() {
  const [status, setStatus] = useState<PayoutFilter>("unpaid");
  const queue = useCursorPages(
    (cursor, signal) =>
      listReferralPayouts(
        { payoutStatus: status === "all" ? null : status, cursor },
        signal,
      ),
    [status],
  );
  // The headline comes from the server's own total, so it is right on every tab
  // and however many pages of the list are loaded.
  const owed = useAsync((signal) => readOwedReferrals(signal), []);
  const [settling, setSettling] = useState<ReferralPayout | null>(null);
  const [reference, setReference] = useState("");
  const close = () => {
    setSettling(null);
    setReference("");
  };
  // A payment recorded as sent is what stops it being sent again, so it is confirmed first.
  const [confirming, setConfirming] = useState<{
    payoutStatus: "paid" | "unpaid";
    payoutReference?: string | null;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const copyFailed = () =>
    setFailure(
      "Your browser would not let us copy. Select the value and copy it by hand.",
    );

  const record = async (
    referral: ReferralPayout,
    input: { payoutStatus: "paid" | "unpaid"; payoutReference?: string | null },
  ) => {
    setBusy(true);
    setFailure(null);
    try {
      await setReferralPayout(referral.id, input);
      close();
      queue.state.reload();
      owed.reload();
    } catch (cause) {
      setFailure(
        errorMessage(cause instanceof Error ? cause : new Error(String(cause))),
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Referral payouts"
        subtitle="What referrers are owed, and what has been sent to them."
      />
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <AsyncBoundary state={owed}>
        {(totals) => (
          <B2CHero title={owedHeadline(totals)}>
            Payments are made outside OSCE Guide, by bank transfer. This page
            records whether each one was sent; it does not send money.
          </B2CHero>
        )}
      </AsyncBoundary>
      <B2CSegmentedTabs
        items={FILTERS}
        value={status}
        onChange={(next) => {
          setStatus(next);
          close();
        }}
        compact
        aria-label="Payout status"
      />
      {settling ? (
        <SettleCard
          referral={settling}
          reference={reference}
          busy={busy}
          onReference={setReference}
          onRecord={(input) =>
            input.payoutStatus === "paid"
              ? setConfirming(input)
              : record(settling, input)
          }
          onClose={close}
          onCopyFailed={copyFailed}
        />
      ) : null}
      {settling ? (
        <ConfirmModal
          isOpen={confirming !== null}
          onCancel={() => setConfirming(null)}
          onConfirm={async () => {
            if (confirming) await record(settling, confirming);
            setConfirming(null);
          }}
          isLoading={busy}
          title="Record this payment as sent?"
          message={`${formatMoney(settling.earned_pence)} to ${settling.referrer_email}. This marks it settled and takes it off the owed list. You can undo it afterwards.`}
          confirmText="Yes, it was sent"
        />
      ) : null}
      <AsyncBoundary
        state={queue.state}
        isEmpty={(items) => items.length === 0}
        empty={{
          title: status === "unpaid" ? "Nothing owed" : "Nothing here",
          description:
            status === "unpaid"
              ? "Every referral that has been redeemed is settled."
              : "No referrals match this filter yet.",
        }}
      >
        {(items) => (
          <>
            <B2CGroupedSection
              eyebrow={FILTERS.find((f) => f.id === status)?.label}
            >
              {items.map((referral) => (
                <B2CGroupedRow
                  key={referral.id}
                  active={settling?.id === referral.id}
                  onClick={() => {
                    setSettling(referral);
                    setReference("");
                  }}
                  title={`${referral.referrer_email} · ${formatMoney(referral.earned_pence)}`}
                  meta={`referred ${referral.referred_email ?? "someone"} · ${
                    referral.redeemed_at
                      ? formatMoment(referral.redeemed_at)
                      : "not redeemed"
                  }${referral.paid_at ? ` · paid ${formatMoment(referral.paid_at)}` : ""}`}
                  trailing={
                    <span className="flex shrink-0 items-center gap-2">
                      {referral.payout_status === "unpaid" &&
                      !referral.payout_details ? (
                        <Badge tone="warning">No bank details</Badge>
                      ) : null}
                      <Badge
                        tone={
                          referral.payout_status === "paid"
                            ? "success"
                            : "warning"
                        }
                      >
                        {referral.payout_status === "paid" ? "Settled" : "Owed"}
                      </Badge>
                    </span>
                  }
                />
              ))}
            </B2CGroupedSection>
            <LoadMore
              hasMore={queue.hasMore}
              busy={queue.loadingMore}
              onLoad={queue.loadMore}
              error={queue.moreError}
            />
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
