"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Input, Modal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { invitePlatformAdmin } from "@/domains/platform/api";

export function InvitePlatformAdminModal({
  open,
  onClose,
  onInvited,
}: {
  open: boolean;
  onClose: () => void;
  onInvited: () => void;
}) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    if (open) setFormKey((key) => key + 1);
  }, [open]);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        const result = await invitePlatformAdmin(email.trim());
        toast.success(
          `${result.user.email} may use the staff console`,
          result.invited
            ? "They have been emailed a link to set their password before they can sign in."
            : "They already had an account and can sign in with their existing password.",
        );
        setEmail("");
        onInvited();
        onClose();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [email, onClose, onInvited, toast],
  );

  if (!open) return null;

  return (
    <Modal onClose={onClose} title="Add platform team member" width="min(32rem, 96vw)">
      <form key={formKey} onSubmit={submit} className="flex flex-col gap-3 p-4 lg:p-6">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

        <p className="text-osce-data text-ink-muted">
          You do not set a password here. If they are new, they get an email with a link to choose one, and must do that before they can sign in.
        </p>

        <Input
          type="email"
          label="Email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={busy}
          autoComplete="off"
        />

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !email.trim()}>
            {busy ? "Adding…" : "Add to team"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
