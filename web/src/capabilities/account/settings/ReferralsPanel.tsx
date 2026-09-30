"use client";

import { useState } from "react";
import {
  HiOutlineCheck,
  HiOutlineDocumentDuplicate,
  HiOutlineInformationCircle,
} from "react-icons/hi2";
import {
  AsyncBoundary,
  Modal,
  ModalHelper,
  ModalPrimaryButton,
  Panel,
  productTokens,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  issueReferralCode,
  readReferrals,
  type Referral,
} from "@/capabilities/account/api";
import BankDetails from "@/capabilities/account/settings/BankDetails";
import ReferralHistory from "@/capabilities/account/settings/ReferralHistory";
import ReferralsInfo from "@/capabilities/account/settings/ReferralsInfo";
import { SettingsTabShell } from "@/capabilities/account/settings/SettingsTabShell";

const { b2cFieldLabel, b2cSettingsFieldInput } = productTokens;

/**
 * Share your referral code, and see what it has earned.
 *
 * The retiring client's Referrals tab (admin-only there, admin-only here): the
 * "Referral program" and "Bank details" cards side by side, then "Referral
 * history". There is nothing to redeem on this screen: a friend's code is
 * applied at checkout, they pay 10% less, and the backend credits the code's
 * owner once Stripe confirms the payment. `earned_pence` is the backend's own
 * tally. Each card loads on its own, as the old ones did.
 */
export default function ReferralsPanel() {
  const referrals = useAsync((signal) => readReferrals(signal), []);
  const [showInfo, setShowInfo] = useState(false);

  return (
    <SettingsTabShell fullWidth>
      <AsyncBoundary state={referrals}>
        {(referral: Referral) => (
          <>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">
              <ReferralCodeCard
                referral={referral}
                onIssued={referrals.reload}
                onShowInfo={() => setShowInfo(true)}
              />
              <BankDetails />
            </div>
            <ReferralHistory />
          </>
        )}
      </AsyncBoundary>

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
    <Panel
      title="Referral program"
      actions={
        <button
          type="button"
          onClick={onShowInfo}
          className="rounded-osce-md p-1 text-ink-subtle transition-colors hover:bg-surface-raised hover:text-accent"
          aria-label="Show referral information"
        >
          <HiOutlineInformationCircle className="h-4 w-4" />
        </button>
      }
    >
      <div className="space-y-4">
        <ModalHelper className="mt-0">
          Share your referral code and earn rewards paid to your bank account.
        </ModalHelper>

        <div className="rounded-osce-md border border-border bg-canvas px-3 py-2.5">
          <p className={b2cFieldLabel}>Total referral earnings</p>
          <p className="mt-0.5 text-osce-body font-semibold tabular-nums text-ink">
            £{(referral.earned_pence / 100).toFixed(2)}
          </p>
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
      </div>
      <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
        {!referral.code ? (
          <ModalPrimaryButton type="button" onClick={handleGenerate} disabled={busy}>
            {busy ? "Generating…" : "Generate code"}
          </ModalPrimaryButton>
        ) : (
          <ModalPrimaryButton
            type="button"
            onClick={handleCopy}
            className={`gap-2 ${copied ? "bg-success" : ""}`}
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
      </div>
    </Panel>
  );
}
