"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useSession } from "@/foundation/session";
import { confirmEmailChange } from "@/foundation/platform-client";
import { errorMessage } from "@/foundation/hooks";
import { authFooterLink, authLink } from "@/foundation/ui/authTheme";
import { boardAlert } from "@/foundation/ui/boardKit";
import AuthShell from "@/capabilities/account/AuthShell";
import AuthButton from "@/capabilities/account/AuthButton";

/**
 * Finish changing the sign-in address from the emailed link.
 *
 * A button, not a call on load: a mail scanner or a prefetch that opens the
 * link would otherwise spend it before the person does. Every session ends
 * when the address moves, so the way on is to sign in again.
 */
export default function ConfirmEmail() {
  const router = useRouter();
  const { status, signOut } = useSession();
  const token = useSearchParams().get("token") ?? "";
  const [email, setEmail] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!token) {
    return (
      <AuthShell variant="card" title="That link is incomplete" subtitle="Use the link in the email we sent to your new address.">
        <p className={authFooterLink}>
          <Link href="/login" className={authLink}>
            Sign in
          </Link>
        </p>
      </AuthShell>
    );
  }

  if (email) {
    return (
      <AuthShell variant="card" title="Email changed" subtitle={`Sign in with ${email} from now on.`}>
        <AuthButton type="button" onClick={() => router.replace("/login")}>
          Sign in
        </AuthButton>
      </AuthShell>
    );
  }

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      const changed = await confirmEmailChange(token);
      if (status !== "anonymous") await signOut();
      setEmail(changed);
    } catch (cause) {
      setError(errorMessage(cause));
      setBusy(false);
    }
  };

  return (
    <AuthShell variant="card" title="Confirm your new email" subtitle="This makes it the address you sign in with, and signs you out everywhere.">
      {error ? (
        <div role="alert" className={boardAlert("bad")}>
          {error}
        </div>
      ) : null}
      <AuthButton type="button" isLoading={busy} onClick={() => void confirm()}>
        {busy ? "Confirming…" : "Confirm new email"}
      </AuthButton>
    </AuthShell>
  );
}
