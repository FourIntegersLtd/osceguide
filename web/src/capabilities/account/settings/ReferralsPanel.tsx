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
  type Referral,
} from "@/capabilities/account/api";
import ReferralsInfo from "@/capabilities/account/settings/ReferralsInfo";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cSettingsCardHeaderIcon, b2cSettingsFieldInput } = productTokens;

/**
 * Share your referral code, and see what it has earned.
 *
 * There is nothing to redeem here: as in b2c, a friend types the code at
 * checkout (see `PlanPicker`), pays 10% less, and the backend credits the code's
 * owner once Stripe confirms the payment. `redeemed_count` and `earned_pence`
 * are the backend's own tally, not a number this screen adds up.
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
          Share your code. Friends get 10% off at checkout, and you earn £2.50 for each 1-month
          plan and £5 for each 3- or 6-month plan they buy.
        </ModalHelper>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-md border border-b2c-border bg-b2c-surface-muted px-3 py-2.5">
            <p className={b2cFieldLabel}>Earned so far</p>
            <p className="mt-0.5 text-osce-body font-semibold tabular-nums text-osce-ink-900">
              £{(referral.earned_pence / 100).toFixed(2)}
            </p>
          </div>
          <div className="rounded-md border border-b2c-border bg-b2c-surface-muted px-3 py-2.5">
            <p className={b2cFieldLabel}>Purchases with your code</p>
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
