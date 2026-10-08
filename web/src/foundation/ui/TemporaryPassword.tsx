"use client";

import { useState } from "react";
import { Alert } from "@/foundation/ui/Alert";
import { Button } from "@/foundation/ui/Button";
import { Checkbox } from "@/foundation/ui/Checkbox";
import { Input } from "@/foundation/ui/Input";
import { generateTemporaryPassword, temporaryPasswordIssue } from "@/foundation/session/temporaryPassword";

/** The password box with a Generate button; the strength rule is the server's. */
export function TemporaryPasswordInput({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex items-end gap-2">
      <div className="min-w-0 flex-1">
        <Input
          label="Temporary password"
          hint="At least 12 characters, mixing letters with numbers, punctuation or capitals."
          error={temporaryPasswordIssue(value)}
          required
          autoComplete="off"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
        />
      </div>
      <Button
        type="button"
        variant="secondary"
        disabled={disabled}
        onClick={() => onChange(generateTemporaryPassword())}
      >
        Generate
      </Button>
    </div>
  );
}

/**
 * "Hand over a password instead of emailing a link", for when the invitation email cannot
 * be delivered. The password is typed in the clear on purpose: the admin has to relay it.
 * It only ever applies to a brand-new account, and must be changed at first sign-in.
 */
export function TemporaryPasswordField({
  enabled,
  onEnabledChange,
  value,
  onChange,
  disabled,
}: {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Checkbox
        label="Set a temporary password instead of emailing a link"
        checked={enabled}
        onChange={(event) => onEnabledChange(event.target.checked)}
        disabled={disabled}
      />
      {enabled ? (
        <>
          <TemporaryPasswordInput value={value} onChange={onChange} disabled={disabled} />
          <p className="text-osce-meta text-ink-subtle">
            Only used if they have no account yet; they must change it when they first sign in.
          </p>
        </>
      ) : null}
    </div>
  );
}

/** True when the form may be submitted: the box is off, or the password is typed and strong enough. */
export function temporaryPasswordReady(enabled: boolean, value: string): boolean {
  return !enabled || (value.length > 0 && temporaryPasswordIssue(value) === null);
}

/** The password just issued, kept on screen to copy until dismissed: it is never shown again after this. */
export function IssuedPassword({
  email,
  password,
  onDismiss,
}: {
  email: string;
  password: string;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(password);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Alert tone="success" title={`Password for ${email}`}>
      <p className="font-mono text-osce-body select-all">{password}</p>
      <p className="mt-1 text-osce-meta text-ink-subtle">
        Tell them privately. They must change it when they first sign in. It is not shown again once you dismiss this.
      </p>
      <div className="mt-2 flex gap-2">
        <Button type="button" size="sm" variant="secondary" onClick={() => void copy()}>
          {copied ? "Copied" : "Copy"}
        </Button>
        <Button type="button" size="sm" variant="secondary" onClick={onDismiss}>
          Done
        </Button>
      </div>
    </Alert>
  );
}
