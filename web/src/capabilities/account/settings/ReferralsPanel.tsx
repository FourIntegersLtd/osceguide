"use client";

import { useState } from "react";
import {
  HiOutlineCheck,
  HiOutlineDocumentDuplicate,
  HiOutlineGift,
  HiOutlineInformationCircle,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  Modal,
  ModalHelper,
  ModalPrimaryButton,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  issueReferralCode,
  readReferrals,
  redeemReferral,
  type Referral,
} from "@/capabilities/account/api";
import ReferralsInfo from "@/capabilities/account/settings/ReferralsInfo";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cSettingsCardHeaderIcon, b2cSettingsFieldInput } = productTokens;

/**
 * Share a code, and redeem one.
 *
 * Both halves, which the retiring client never had together: codes could be
 * issued and never redeemed, so a referrer earned nothing and nobody could see
 * why. `redeemed_count` and `earned_pence` are the backend's own tally, not a
 * number this screen adds up.
 */
export default function ReferralsPanel() {
  const referrals = useAsync((signal) => readReferrals(signal), []);
  const [showInfo, setShowInfo] = useState(false);

  return (
    <SettingsTabShell fullWidth>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">
        <AsyncBoundary state={referrals}>
          {(referral: Referral) => (
            <ReferralCodeCard
              referral={referral}
              onIssued={referrals.reload}
              onShowInfo={() => setShowInfo(true)}
            />
          )}
        </AsyncBoundary>
        <RedeemCard onRedeemed={referrals.reload} />
      </div>

      {showInfo ? (
        <Modal
          width="600px"
          height="fit-content"
          title="Understanding our referral program"
          onClose={() => setShowInfo(false)}
        >
          <ReferralsInfo />
        </Modal>
      ) : null}
    </SettingsTabShell>
  );
}

function ReferralCodeCard({
  referral,
  onIssued,
  onShowInfo,
}: {
  referral: Referral;
  onIssued: () => void;
  onShowInfo: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    setError(null);
    setBusy(true);
    try {
      await issueReferralCode();
      onIssued();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(referral.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Your browser would not let us copy. Select the code and copy it by hand.");
    }
  };

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>
        <HiOutlineGift className={b2cSettingsCardHeaderIcon} aria-hidden />
        Referral program
        <button
          type="button"
          onClick={onShowInfo}
          className="ml-auto rounded-md p-1 text-b2c-text-muted transition-colors hover:bg-osce-surface hover:text-osce-accent-hover"
          aria-label="Show referral information"
        >
          <HiOutlineInformationCircle className="h-4 w-4" />
        </button>
      </B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">
        <ModalHelper className="mt-0">
          Share your code. Redemptions are counted here. The balance is recorded and is not paid out.
        </ModalHelper>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-b2c-border bg-b2c-surface-muted px-3 py-2.5">
            <p className={b2cFieldLabel}>Recorded balance (not paid out)</p>
            <p className="mt-0.5 text-osce-body font-semibold tabular-nums text-osce-ink-900">
              £{(referral.earned_pence / 100).toFixed(2)}
            </p>
          </div>
          <div className="rounded-md border border-b2c-border bg-b2c-surface-muted px-3 py-2.5">
            <p className={b2cFieldLabel}>People who redeemed</p>
            <p className="mt-0.5 text-osce-body font-semibold tabular-nums text-osce-ink-900">
              {referral.redeemed_count}
            </p>
          </div>
        </div>

        <div>
          <label htmlFor="referral-code" className={b2cFieldLabel}>
            Your referral code
          </label>
          <input
            id="referral-code"
            className={`mt-1.5 ${b2cSettingsFieldInput}`}
            value={referral.code}
            readOnly
            placeholder="Generate your referral code"
          />
          {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
        </div>
      </B2CPanelCardBody>
      <B2CPanelCardFooter>
        {!referral.code ? (
          <ModalPrimaryButton type="button" onClick={handleGenerate} disabled={busy}>
            {busy ? "Generating…" : "Generate code"}
          </ModalPrimaryButton>
        ) : (
          <ModalPrimaryButton
            type="button"
            onClick={handleCopy}
            className={`gap-2 ${copied ? "bg-osce-success-solid hover:bg-osce-success-solid-hover" : ""}`}
          >
            {copied ? (
              <>
                <HiOutlineCheck className="h-3.5 w-3.5" />
                Copied!
              </>
            ) : (
              <>
                <HiOutlineDocumentDuplicate className="h-3.5 w-3.5" />
                Copy code
              </>
            )}
          </ModalPrimaryButton>
        )}
      </B2CPanelCardFooter>
    </B2CPanelCard>
  );
}

function RedeemCard({ onRedeemed }: { onRedeemed: () => void }) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const handleRedeem = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await redeemReferral(code.trim());
      setDone(true);
      setCode("");
      onRedeemed();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={handleRedeem}>
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <HiOutlineGift className={b2cSettingsCardHeaderIcon} aria-hidden />
          Somebody referred you?
        </B2CPanelCardHeader>
        <B2CPanelCardBody className="space-y-4">
          <ModalHelper className="mt-0">
            Enter their code once. It is counted against their referrals when you do.
          </ModalHelper>
          <div>
            <label htmlFor="redeem-code" className={b2cFieldLabel}>
              Referral code
            </label>
            <input
              id="redeem-code"
              className={`mt-1.5 ${b2cSettingsFieldInput}`}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="Their code"
            />
            {error ? <p className="mt-1 text-osce-meta text-osce-danger">{error}</p> : null}
            {done ? (
              <p className="mt-1 text-osce-meta text-osce-success-text">
                Redeemed. Thank them for us.
              </p>
            ) : null}
          </div>
        </B2CPanelCardBody>
        <B2CPanelCardFooter>
          <ModalPrimaryButton type="submit" disabled={busy || code.trim().length === 0}>
            {busy ? "Redeeming…" : "Redeem code"}
          </ModalPrimaryButton>
        </B2CPanelCardFooter>
      </B2CPanelCard>
    </form>
  );
}
