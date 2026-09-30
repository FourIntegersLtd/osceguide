"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { HiOutlineArrowPath, HiOutlineTrash } from "react-icons/hi2";
import {
  ConfirmModal,
  ModalDangerButton,
  ModalHelper,
  Panel,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { closeAccount } from "@/capabilities/account/api";

const { b2cInputBase } = productTokens;

/**
 * The retiring screen's "Danger zone": close the signed-in account.
 *
 * The row stays, so consultations and payments still have someone they
 * belonged to. Sign-in stops, and the password is cleared. The backend asks
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
      <Panel title="Danger zone">
        <div className="space-y-3">
          <p className="text-osce-body font-semibold text-osce-danger">Delete your account</p>
          <ModalHelper className="mt-0">
            This action cannot be undone and you will not be able to restore your account.
          </ModalHelper>
          {isAdmin ? <ModalHelper>Admin accounts cannot be deleted from Settings.</ModalHelper> : null}
        </div>
        <div className="mt-6 flex justify-end gap-3 border-t border-border pt-4">
          <ModalDangerButton
            type="button"
            onClick={() => setOpen(true)}
            disabled={isAdmin || busy}
            className="gap-2"
          >
            {busy ? (
              <>
                <HiOutlineArrowPath className="h-4 w-4 animate-spin" aria-hidden />
                Deleting...
              </>
            ) : (
              <>
                <HiOutlineTrash className="h-4 w-4" aria-hidden />
                Delete Account
              </>
            )}
          </ModalDangerButton>
        </div>
      </Panel>

      <ConfirmModal
        isOpen={open}
        onCancel={reset}
        onConfirm={() => void close()}
        title="Delete your account?"
        message="This permanently removes your account, your attempts and all your feedback. Any active subscription ends. Type DELETE to confirm."
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
