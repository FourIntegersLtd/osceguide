"use client";

import { useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Button, Input } from "@/foundation/ui";
import { groupSecret, isCompleteTotp, normaliseTotp } from "@/capabilities/account/mfa/codes";

/**
 * Add the account to an authenticator app, then prove it with a code.
 *
 * On a computer the phone scans the QR code; on a phone the `otpauth://` link
 * opens the installed authenticator directly. The key is the fallback for apps
 * that do neither. The QR code stays dark on white in both themes so it scans.
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
      <p className="text-osce-body text-ink">
        After setup, every sign-in needs your password and a 6-digit code from your authenticator
        app.
      </p>
      <ol className="list-decimal space-y-3 pl-5 text-osce-body text-ink">
        <li>
          Open an authenticator app such as Google Authenticator, Microsoft Authenticator or
          1Password and scan this code.
          <QRCodeSVG
            value={otpauthUri}
            size={176}
            marginSize={2}
            bgColor="#ffffff"
            fgColor="#000000"
            title="QR code for your authenticator app"
            className="my-2 block rounded-osce-lg border border-border"
          />
          <span className="block">
            Setting up on the phone that has the authenticator app? Tap{" "}
            <a href={otpauthUri} className="font-medium text-accent hover:text-accent-hover">
              Open in your authenticator app
            </a>{" "}
            instead of scanning.
          </span>
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
