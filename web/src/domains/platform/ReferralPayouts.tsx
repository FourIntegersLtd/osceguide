"use client";

import { Fragment, useState } from "react";
import { LuHandCoins } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Badge,
  Button,
  Input,
  Panel,
  PlatformPageHeader,
  Row,
  RowList,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  listReferralPayouts,
  setReferralPayout,
  type ReferralPayout,
} from "@/domains/platform/api";
import { formatMoment } from "@/domains/platform/support";

type PayoutFilter = "unpaid" | "paid" | "all";

const FILTERS: B2CSegmentedTabItem<PayoutFilter>[] = [
  { id: "unpaid", label: "Owed" },
  { id: "paid", label: "Settled" },
  { id: "all", label: "Everything" },
];

function pounds(pence: number): string {
  return `£${(pence / 100).toFixed(2)}`;
}

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
        onClick={() => void copy()}
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
export function ReferralPayouts() {
  const [status, setStatus] = useState<PayoutFilter>("unpaid");
  const queue = useAsync(
    (signal) =>
      listReferralPayouts(
        { payoutStatus: status === "all" ? null : status },
        signal,
      ),
    [status],
  );
  const [settling, setSettling] = useState<ReferralPayout | null>(null);
  const [reference, setReference] = useState("");
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
      setSettling(null);
      setReference("");
      queue.reload();
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
      <PlatformPageHeader
        title="Referral payouts"
        description="What referrers are owed, and what has been sent to them."
        icon={LuHandCoins}
      />
      {failure ? <Alert tone="danger">{failure}</Alert> : null}
      <Panel
        title="The queue"
        description="Settled outside the product. This is the record of whether a transfer was made, not a way to make one."
        actions={
          <B2CSegmentedTabs
            items={FILTERS}
            value={status}
            onChange={setStatus}
            compact
            aria-label="Payout status"
          />
        }
        padding="none"
      >
        <AsyncBoundary
          state={queue}
          isEmpty={(page) => page.items.length === 0}
          empty={{
            title: status === "unpaid" ? "Nothing owed" : "Nothing here",
            description:
              status === "unpaid"
                ? "Every referral that has been redeemed is settled."
                : "No referrals match this filter yet.",
            bare: true,
          }}
        >
          {(page) => (
            <RowList flush>
              {page.items.map((referral) => (
                <Fragment key={referral.id}>
                  <Row>
                    <div className="min-w-0">
                      <p className="text-osce-data font-medium text-ink">
                        {referral.referrer_email} ·{" "}
                        {pounds(referral.earned_pence)}
                      </p>
                      <p className="truncate text-osce-meta text-ink-subtle">
                        referred {referral.referred_email ?? "someone"} ·{" "}
                        {referral.redeemed_at
                          ? formatMoment(referral.redeemed_at)
                          : "not redeemed"}
                        {referral.paid_at
                          ? ` · paid ${formatMoment(referral.paid_at)}`
                          : ""}
                      </p>
                      {referral.payout_reference ? (
                        <p className="mt-1 text-osce-meta text-ink-muted">
                          Reference {referral.payout_reference}
                        </p>
                      ) : null}
                      {referral.payout_status === "unpaid" ? (
                        referral.payout_details ? (
                          <PayTo
                            details={referral.payout_details}
                            onCopyFailed={copyFailed}
                          />
                        ) : (
                          <NoBankDetails />
                        )
                      ) : null}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
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
                      {referral.payout_status === "paid" ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            void record(referral, { payoutStatus: "unpaid" })
                          }
                        >
                          Not paid after all
                        </Button>
                      ) : (
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            setSettling(referral);
                            setReference("");
                          }}
                        >
                          Mark paid
                        </Button>
                      )}
                    </div>
                  </Row>
                  {/* Under the row it settles, which already shows where to pay:
                      at the foot of a long queue it opened off screen. */}
                  {settling?.id === referral.id ? (
                    <Row className="flex-col items-stretch gap-3">
                      <div className="min-w-0">
                        <p className="text-osce-data font-medium text-ink">
                          Mark {pounds(settling.earned_pence)} to{" "}
                          {settling.referrer_email} as paid
                        </p>
                        <p className="mt-2 text-osce-meta text-ink-subtle">
                          The transfer&rsquo;s own reference, so this row can be
                          found on a statement later. Optional.
                        </p>
                      </div>
                      <Input
                        label="Payment reference"
                        value={reference}
                        onChange={(event) => setReference(event.target.value)}
                        placeholder="e.g. FT-2026-09-24"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          disabled={busy}
                          onClick={() =>
                            void record(settling, {
                              payoutStatus: "paid",
                              payoutReference: reference.trim() || null,
                            })
                          }
                        >
                          Record payment
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          disabled={busy}
                          onClick={() => {
                            setSettling(null);
                            setReference("");
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </Row>
                  ) : null}
                </Fragment>
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>
    </div>
  );
}
