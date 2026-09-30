"use client";

import { useState } from "react";
import { Button, Input } from "@/foundation/ui";
import { groupSecret, isCompleteTotp, normaliseTotp } from "@/capabilities/account/mfa/codes";

/**
 * Add the account to an authenticator app, then prove it with a code.
 *
 * There is no QR code: drawing one needs a new dependency, and the two ways
 * shown cover every app. On a phone the `otpauth://` link opens the installed
 * authenticator directly; on a computer the key is typed in by hand.
 */
export function AuthenticatorSetup({
  secret,
  otpauthUri,
  busy,
  error,
  onConfirm,
}: {
  secret: string;
  otpauthUri: string;
  busy: boolean;
  error: string | null;
  onConfirm: (code: string) => void;
}) {
  const [code, setCode] = useState("");

  return (
    <form
      className="space-y-4"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (isCompleteTotp(code)) onConfirm(normaliseTotp(code));
      }}
    >
      <ol className="list-decimal space-y-3 pl-5 text-osce-body text-ink">
        <li>
          Open an authenticator app such as Google Authenticator, Microsoft Authenticator or
          1Password.{" "}
          <a href={otpauthUri} className="font-medium text-accent hover:text-accent-hover">
            Open in your authenticator app
          </a>{" "}
          if you are on your phone.
        </li>
        <li>
          Or add an account by hand with this setup key:
          <code className="mt-2 block select-all break-all rounded-osce-lg border border-border bg-canvas px-3 py-2 font-mono text-osce-data text-ink">
            {groupSecret(secret)}
          </code>
        </li>
        <li>Enter the six-digit code the app shows.</li>
      </ol>
      <Input
        label="Code from your app"
        name="code"
        inputMode="numeric"
        autoComplete="one-time-code"
        value={code}
        onChange={(event) => setCode(event.target.value)}
        error={error}
      />
      <Button type="submit" fullWidth isLoading={busy} disabled={!isCompleteTotp(code)}>
        {busy ? "Checking…" : "Turn on two-factor sign-in"}
      </Button>
    </form>
  );
}
