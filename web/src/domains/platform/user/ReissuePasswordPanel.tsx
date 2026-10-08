"use client";

import { useState } from "react";
import { Alert, Button, Panel } from "@/foundation/ui";
import { IssuedPassword, TemporaryPasswordField } from "@/foundation/ui/TemporaryPassword";
import { errorMessage } from "@/foundation/hooks";
import { reissueTemporaryPassword } from "@/domains/platform/user/api";
import { temporaryPasswordIssue } from "@/foundation/session/temporaryPassword";

/**
 * A new temporary password for an account that has not yet changed the one it was
 * handed. Offered only while `must_change_password` is set: once the person chose their
 * own, the server refuses and the console sends a reset link instead.
 */
export function ReissuePasswordPanel({ userId, email }: { userId: string; email: string }) {
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [issued, setIssued] = useState<string | null>(null);
  const issue = temporaryPasswordIssue(password);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await reissueTemporaryPassword(userId, password);
      setIssued(password);
      setPassword("");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Temporary password"
      description="They have not changed the password they were given yet. If it was lost, issue a new one; the old one stops working and they are signed out."
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {issued !== null ? (
          <IssuedPassword email={email} password={issued} onDismiss={() => setIssued(null)} />
        ) : null}
        <TemporaryPasswordField
          toggle={false}
          enabled
          onEnabledChange={() => undefined}
          value={password}
          onChange={setPassword}
          disabled={busy}
          hint="At least 12 characters, mixing letters with numbers, punctuation or capitals."
        />
        <div>
          <Button type="submit" disabled={busy || password.length === 0 || issue !== null}>
            {busy ? "Issuing…" : "Issue"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
