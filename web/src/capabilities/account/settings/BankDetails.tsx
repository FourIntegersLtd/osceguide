"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { HiOutlineArrowPath, HiOutlineBanknotes } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardFooter,
  B2CPanelCardHeader,
  ModalField,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  readPayoutDetails,
  savePayoutDetails,
  type PayoutDetails,
} from "@/capabilities/account/api";

/** The old card's own input class, kept verbatim so the four fields look as they did. */
const inputClassName =
  "w-full rounded-md border border-b2c-border bg-osce-surface px-3 py-2.5 text-osce-body text-osce-ink-900 outline-none transition focus:border-osce-accent focus:ring-2 focus:ring-osce-accent-subtle disabled:cursor-not-allowed disabled:bg-b2c-secondary disabled:opacity-50";

/** How a saved account number is shown while the field is not being edited. */
function maskedAccountNumber(lastFour: string): string {
  return `****${lastFour}`;
}

/**
 * Where referral rewards are paid: the retiring client's "Bank details" card.
 *
 * Same four fields, same strings, same masking of the account number. One
 * difference sits under the surface: the old client kept the number in plain
 * text and put it back in the field on focus. `platform-api` stores it
 * encrypted and only ever returns its last four digits, so focusing the field
 * empties it for a new number, and saving with it left alone keeps the stored
 * one.
 */
export default function BankDetails() {
  const state = useAsync((signal) => readPayoutDetails(signal), []);

  if (state.loading && state.data === null) return <BankDetailsLoading />;

  return (
    <AsyncBoundary state={state}>
      {({ details }) => <BankDetailsForm key={details?.updated_at ?? "new"} saved={details} />}
    </AsyncBoundary>
  );
}

function BankDetailsHeader() {
  return (
    <B2CPanelCardHeader>
      <HiOutlineBanknotes className="h-3.5 w-3.5 shrink-0 text-osce-accent" aria-hidden />
      Bank details
    </B2CPanelCardHeader>
  );
}

function BankDetailsLoading() {
  return (
    <B2CPanelCard className="mt-0 h-full">
      <BankDetailsHeader />
      <B2CPanelCardBody>
        <div className="flex items-center justify-center gap-2 py-8 text-osce-body text-b2c-text-muted">
          <HiOutlineArrowPath className="h-4 w-4 animate-spin" />
          Loading bank details…
        </div>
      </B2CPanelCardBody>
    </B2CPanelCard>
  );
}

function BankDetailsForm({ saved }: { saved: PayoutDetails | null }) {
  const [form, setForm] = useState({
    bank_name: saved?.bank_name ?? "",
    account_name: saved?.account_holder_name ?? "",
    sort_code: saved?.sort_code ?? "",
  });
  // A new number typed this visit. Empty means "keep the one on file".
  const [accountNumber, setAccountNumber] = useState("");
  const [lastFour, setLastFour] = useState(saved?.account_number_last4 ?? "");
  const [isEditingAccountNumber, setIsEditingAccountNumber] = useState(saved === null);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const hasStoredNumber = lastFour.length > 0;

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    if (name === "account_number") {
      setAccountNumber(value);
      return;
    }
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const handleAccountNumberFocus = () => setIsEditingAccountNumber(true);

  const handleAccountNumberBlur = () => {
    setIsEditingAccountNumber(!accountNumber && !hasStoredNumber);
  };

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setIsSaving(true);
    setSubmitError(null);
    setSuccessMessage(null);
    try {
      const stored = await savePayoutDetails({
        bank_name: form.bank_name,
        account_holder_name: form.account_name,
        sort_code: form.sort_code,
        account_number: accountNumber || null,
      });
      setSuccessMessage("Bank details submitted successfully!");
      setLastFour(stored.account_number_last4);
      setAccountNumber("");
      setIsEditingAccountNumber(false);
    } catch (cause) {
      setSubmitError(errorMessage(cause));
    } finally {
      setIsSaving(false);
    }
  };

  const accountNumberValue = isEditingAccountNumber
    ? accountNumber
    : accountNumber || (hasStoredNumber ? maskedAccountNumber(lastFour) : "");

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="h-full">
      <B2CPanelCard className="mt-0 h-full">
        <BankDetailsHeader />
        <B2CPanelCardBody className="space-y-4">
          <div>
            <ModalTitle className="text-osce-body">Account information</ModalTitle>
            <ModalHelper>Add your bank details to receive referral payouts.</ModalHelper>
          </div>

          {successMessage ? (
            <div
              className="rounded-md border border-osce-success-border bg-osce-success-bg px-3 py-2.5 text-osce-meta text-osce-success-text"
              role="alert"
            >
              {successMessage}
            </div>
          ) : null}
          {submitError ? (
            <div
              className="rounded-md border border-osce-danger-border bg-osce-danger-bg px-3 py-2.5 text-osce-meta text-osce-danger-text"
              role="alert"
            >
              {submitError}
            </div>
          ) : null}

          <ModalField label="Bank name" htmlFor="bank_name">
            <input
              id="bank_name"
              type="text"
              name="bank_name"
              value={form.bank_name}
              onChange={handleChange}
              placeholder="Enter bank name"
              className={inputClassName}
              required
              disabled={isSaving}
            />
          </ModalField>
          <ModalField label="Account number" htmlFor="account_number">
            <input
              id="account_number"
              type={isEditingAccountNumber ? "text" : "password"}
              name="account_number"
              inputMode="numeric"
              autoComplete="off"
              value={accountNumberValue}
              onChange={handleChange}
              onFocus={handleAccountNumberFocus}
              onBlur={handleAccountNumberBlur}
              placeholder={!isEditingAccountNumber && !hasStoredNumber ? "Enter account number" : ""}
              className={inputClassName}
              required={!hasStoredNumber}
              disabled={isSaving}
            />
          </ModalField>
          <ModalField label="Account holder name" htmlFor="account_name">
            <input
              id="account_name"
              type="text"
              name="account_name"
              value={form.account_name}
              onChange={handleChange}
              placeholder="Enter account holder name"
              className={inputClassName}
              required
              disabled={isSaving}
            />
          </ModalField>
          <ModalField label="Sort code" htmlFor="sort_code">
            <input
              id="sort_code"
              type="text"
              name="sort_code"
              value={form.sort_code}
              onChange={handleChange}
              pattern="[0-9]{2}-?[0-9]{2}-?[0-9]{2}"
              title="Sort code should be in XX-XX-XX or XXXXXX format"
              placeholder="e.g., 12-34-56 or 123456"
              className={inputClassName}
              required
              disabled={isSaving}
            />
          </ModalField>
        </B2CPanelCardBody>
        <B2CPanelCardFooter>
          <ModalPrimaryButton type="submit" disabled={isSaving}>
            {isSaving ? "Saving…" : "Save bank details"}
          </ModalPrimaryButton>
        </B2CPanelCardFooter>
      </B2CPanelCard>
    </form>
  );
}
