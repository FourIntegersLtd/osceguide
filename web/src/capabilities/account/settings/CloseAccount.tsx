"use client";

import { ACCOUNT_REOPEN_DAYS } from "@/foundation/config/copyNumbers";
import { useState } from "react";
import { HiOutlineArrowPath, HiOutlineTrash } from "react-icons/hi2";
import { Button, ConfirmModal, productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { closeAccount } from "@/capabilities/account/api";
import { settingsMeta, settingsSub } from "@/capabilities/account/settings/SettingsKit";

const { b2cInputBase } = productTokens;

/**
 * The grey block that ends the Profile tab: close the signed-in account.
 *
 * The row stays for 30 days, then erasure runs (`service_erasure`), so
 * consultations and payments still have someone they belonged to until
 * then. Sign-in stops at once, and the password is cleared. The backend asks
 * for the password when the account has one and for the word "delete" when it
 * does not (organisation sign-in), so the modal collects both and sends both.
 * Platform admins are refused here, as they were on the old screen.
 */
export function CloseAccount({ isAdmin }: { isAdmin: boolean }) {
  const { signOut } = useSession();
  const [step, setStep] = useState<"closed" | "form" | "final">("closed");
  const [confirmText, setConfirmText] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setStep("closed");
    setConfirmText("");
    setPassword("");
    setError(null);
  };

  const close = async () => {
    setBusy(true);
    setError(null);
    try {
      await closeAccount({ password: password || null, confirm: confirmText.trim().toLowerCase() });
      // Through `signOut`: RequireSession sends a signed-out tab to the page it names, and a
      // separate replace here lost the race to it (the notice never showed).
      await signOut("/login?deleted=1");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="flex flex-wrap items-center justify-between gap-4 rounded-osce-lg bg-canvas p-6">
        <div className="min-w-0 flex-1">
          <h2 className="text-osce-subheading font-semibold text-danger">Delete your account</h2>
          <p className={settingsSub}>You are signed out straight away. You have {ACCOUNT_REOPEN_DAYS} days to reopen it.</p>
          {isAdmin ? (
            <p className={`mt-1 ${settingsMeta}`}>Admin accounts cannot be deleted from Settings.</p>
          ) : null}
        </div>
        <Button
          variant="danger"
          onClick={() => setStep("form")}
          disabled={isAdmin || busy}
          className="shrink-0 gap-2"
        >
          {busy ? (
            <>
              <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden />
              Deleting...
            </>
          ) : (
            <>
              <HiOutlineTrash className="h-4 w-4" aria-hidden />
              Delete account
            </>
          )}
        </Button>
      </section>

      <ConfirmModal
        isOpen={step === "form"}
        onCancel={reset}
        onConfirm={() => setStep("final")}
        title="Delete your account?"
        message="Here is what happens."
        confirmText="Continue"
        cancelText="Keep account"
        tone="danger"
        confirmDisabled={confirmText.trim().toUpperCase() !== "DELETE"}
        error={error}
      >
        <div className="space-y-3 text-left">
          <ul className="list-disc space-y-1 pl-5 text-osce-body text-ink">
            <li>Now: you are signed out, paid access ends with the account, and there is no refund.</li>
            <li>For {ACCOUNT_REOPEN_DAYS} days: sign in again to reopen the account.</li>
            <li>After {ACCOUNT_REOPEN_DAYS} days: your details, attempts and feedback are erased.</li>
          </ul>
          <label className="block">
            <span className="mb-1 block text-osce-meta text-ink-subtle">
              Type <span className="font-mono font-semibold">DELETE</span> to confirm
            </span>
            <input
              type="text"
              autoComplete="off"
              value={confirmText}
              onChange={(event) => setConfirmText(event.target.value)}
              className={b2cInputBase}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-osce-meta text-ink-subtle">
              Password (leave blank if you sign in through your organisation)
            </span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={b2cInputBase}
            />
          </label>
        </div>
      </ConfirmModal>

      <ConfirmModal
        isOpen={step === "final"}
        onCancel={() => setStep("form")}
        onConfirm={close}
        title="Delete your account?"
        message={`This cannot be undone after ${ACCOUNT_REOPEN_DAYS} days.`}
        confirmText="Delete my account"
        cancelText="Back"
        tone="danger"
        isLoading={busy}
        error={error}
      />
    </>
  );
}
