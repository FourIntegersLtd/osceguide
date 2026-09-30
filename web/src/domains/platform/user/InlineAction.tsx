"use client";

import { useCallback, useState, type ReactNode } from "react";
import { Alert, Button, Input } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";

/**
 * A button that unfolds into a reason and a confirm.
 *
 * Every write the console makes on somebody's behalf is audited with why, so
 * the reason is asked for at the moment of acting rather than reconstructed
 * later. Inline rather than a modal: a support conversation is a run of these
 * and a modal per step is a dialog storm.
 */
export function InlineAction({
  label,
  confirmLabel,
  tone = "default",
  reasonLabel = "Reason",
  requireReason = true,
  description,
  onConfirm,
  disabled,
  children,
}: {
  label: string;
  confirmLabel?: string;
  tone?: "default" | "danger";
  reasonLabel?: string;
  requireReason?: boolean;
  description?: ReactNode;
  onConfirm: (reason: string) => Promise<void>;
  disabled?: boolean;
  /** Extra fields, rendered above the reason. */
  children?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const confirm = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await onConfirm(reason.trim());
      setOpen(false);
      setReason("");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [onConfirm, reason]);

  if (!open) {
    return (
      <Button
        variant={tone === "danger" ? "danger" : "secondary"}
        size="sm"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {label}
      </Button>
    );
  }

  return (
    <div className="flex w-full flex-col gap-2 rounded-md border border-b2c-border bg-surface-raised p-3">
      {description ? <p className="text-osce-meta text-ink-muted">{description}</p> : null}
      {error ? <Alert tone="danger">{error}</Alert> : null}
      {children}
      <Input
        label={reasonLabel}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        disabled={busy}
        hint="Goes in the audit log."
      />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" size="sm" disabled={busy} onClick={() => setOpen(false)}>
          Cancel
        </Button>
        <Button
          variant={tone === "danger" ? "danger" : "primary"}
          size="sm"
          disabled={busy || (requireReason && !reason.trim())}
          onClick={() => void confirm()}
        >
          {busy ? "Working…" : (confirmLabel ?? label)}
        </Button>
      </div>
    </div>
  );
}
