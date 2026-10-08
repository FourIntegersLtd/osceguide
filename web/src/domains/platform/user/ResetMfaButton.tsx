"use client";

import { useState } from "react";
import { Button, ConfirmModal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { resetUserMfa } from "@/domains/platform/user/api";

/** Clears a lost authenticator; they enrol again at next sign-in. Refused if none is enrolled. */
export function ResetMfaButton({ userId, email }: { userId: string; email: string }) {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await resetUserMfa(userId);
      toast.success("Authenticator reset", "They will enrol a new one the next time they sign in.");
      setOpen(false);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Reset authenticator
      </Button>
      <ConfirmModal
        isOpen={open}
        onCancel={() => {
          setOpen(false);
          setError(null);
        }}
        onConfirm={() => confirm()}
        isLoading={busy}
        error={error}
        tone="danger"
        title="Reset this authenticator?"
        confirmText="Reset"
        message={`${email} loses their current authenticator and must enrol a new one at their next sign-in. Use this only when they have lost it.`}
      />
    </>
  );
}
