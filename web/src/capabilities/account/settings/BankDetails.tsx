"use client";

import { useState, type ChangeEvent, type FormEvent } from "react";
import { HiOutlineArrowPath } from "react-icons/hi2";
import {
  AsyncBoundary,
  ModalField,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
  Panel,
} from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  readPayoutDetails,
  savePayoutDetails,
  type PayoutDetails,
} from "@/capabilities/account/api";

/** The old card's own input class, kept verbatim so the four fields look as they did. */
const inputClassName =
  "w-full rounded-osce-md border border-border bg-surface px-3 py-2.5 text-osce-body text-ink outline-none transition focus:border-osce-accent focus:ring-2 focus:ring-osce-accent-subtle disabled:cursor-not-allowed disabled:bg-surface-raised disabled:opacity-50";

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

function BankDetailsLoading() {
  return (
    <Panel title="Bank details" className="h-full">
      <div className="flex items-center justify-center gap-2 py-8 text-osce-body text-ink-subtle">
        <HiOutlineArrowPath className="h-4 w-4 animate-spin" />
        Loading bank details…
      </div>
    </Panel>
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
      <Panel title="Bank details" className="h-full">
        <div className="space-y-4">
          <div>
            <ModalTitle className="text-osce-body">Account information</ModalTitle>
            <ModalHelper>Add your bank details to receive referral payouts.</ModalHelper>
          </div>

          {successMessage ? (
            <div
              className="rounded-osce-md border border-osce-success-border bg-osce-success-bg px-3 py-2.5 text-osce-meta text-osce-success-text"
              role="alert"
            >
              {successMessage}
            </div>
          ) : null}
          {submitError ? (
            <div
              className="rounded-osce-md border border-osce-danger-border bg-osce-danger-bg px-3 py-2.5 text-osce-meta text-osce-danger-text"
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
        </div>
        <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
          <ModalPrimaryButton type="submit" disabled={isSaving}>
            {isSaving ? "Saving…" : "Save bank details"}
          </ModalPrimaryButton>
        </div>
      </Panel>
    </form>
  );
}
