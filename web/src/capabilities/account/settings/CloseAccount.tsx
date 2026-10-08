"use client";

import { ACCOUNT_REOPEN_DAYS } from "@/foundation/config/copyNumbers";
import { useState } from "react";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  const { signOut } = useSession();
  const [open, setOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setOpen(false);
    setConfirmText("");
    setPassword("");
    setError(null);
  };

  const close = async () => {
    setBusy(true);
    setError(null);
    try {
      await closeAccount({ password: password || null, confirm: confirmText.trim().toLowerCase() });
      await signOut();
      router.replace("/login?deleted=1");
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
          <p className={settingsSub}>
            You are signed out straight away. Sign in again within {ACCOUNT_REOPEN_DAYS} days to reopen it; after that your details and practice are erased.
          </p>
          {isAdmin ? (
            <p className={`mt-1 ${settingsMeta}`}>Admin accounts cannot be deleted from Settings.</p>
          ) : null}
        </div>
        <Button
          variant="danger"
          onClick={() => setOpen(true)}
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
        isOpen={open}
        onCancel={reset}
        onConfirm={() => close()}
        title="Delete your account?"
        message={`You will be signed out now. Sign in again within ${ACCOUNT_REOPEN_DAYS} days to reopen the account; after that your details, attempts and feedback are erased. Closing does not cancel a subscription or refund a payment: email support first if you want that. Type DELETE to confirm.`}
        confirmText="Delete my account"
        cancelText="Keep account"
        tone="danger"
        isLoading={busy}
        confirmDisabled={confirmText.trim().toUpperCase() !== "DELETE"}
        error={error}
      >
        <div className="space-y-3 text-left">
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
    </>
  );
}
