"use client";

import { useState } from "react";
import { temporaryPasswordReady } from "@/foundation/ui/TemporaryPassword";

/** What the add routes answer beyond the generated type, until it is regenerated. */
export type WithTemporaryPassword = { temporary_password_applied?: boolean };

/**
 * The state every "hand over a password instead of emailing a link" form shares: the
 * checkbox, the typed password, and the password just issued (kept to copy until dismissed).
 */
export function useTemporaryPassword() {
  const [enabled, setEnabled] = useState(false);
  const [value, setValue] = useState("");
  const [issued, setIssued] = useState<{ email: string; password: string } | null>(null);
  return {
    /** Spread onto `TemporaryPasswordField`. */
    field: { enabled, onEnabledChange: setEnabled, value, onChange: setValue },
    /** False while the box is ticked and the password is empty or too weak. */
    ready: temporaryPasswordReady(enabled, value),
    /** What to send: the password, only when the box is ticked. */
    typed: enabled ? value : undefined,
    issued,
    dismiss: () => setIssued(null),
    /** After a successful submit: show the password if the server used it; clear the form. */
    finish: (email: string, applied: boolean) => {
      setIssued(applied ? { email, password: value } : null);
      setValue("");
      setEnabled(false);
    },
  };
}
