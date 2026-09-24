"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { closeAccount } from "@/capabilities/account/api";

/**
 * Close the signed-in account.
 *
 * The row stays, so consultations and payments still have someone they
 * belonged to. Sign-in stops, and the password is cleared.
 */
export function CloseAccount() {
  const router = useRouter();
  const { signOut } = useSession();
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const close = async () => {
    setBusy(true);
    setError(null);
    try {
      await closeAccount({ password: password || null, confirm: password ? null : "delete" });
      await signOut();
      router.replace("/login?deleted=1");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mt-8 rounded-lg border border-osce-danger/30 p-4">
      <h2 className="text-osce-body font-semibold text-osce-ink-900">Close account</h2>
      <p className="mt-1 text-osce-meta text-b2c-text-muted">
        You will be signed out and will not be able to sign in again. Your past consultations stay on record.
      </p>
      {open ? (
        <div className="mt-3 space-y-3">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <label className="block text-osce-meta text-b2c-text-muted">
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full max-w-sm rounded-md border border-osce-border bg-white px-3 py-2 text-osce-body text-osce-ink-900"
              autoComplete="current-password"
            />
          </label>
          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)} disabled={busy}>
              Cancel
            </Button>
            <Button type="button" variant="danger" isLoading={busy} onClick={() => void close()}>
              Close my account
            </Button>
          </div>
        </div>
      ) : (
        <Button type="button" variant="danger" className="mt-3" onClick={() => setOpen(true)}>
          Close account
        </Button>
      )}
    </section>
  );
}
