"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { seatMembership } from "@/domains/platform/api";
import { Section } from "@/domains/platform/chrome";
import { SEAT_ROLES } from "@/domains/platform/support";

/**
 * Seat the first administrator of a freshly provisioned organisation.
 *
 * Every other membership is added by an org admin, inside the organisation. A
 * new tenant has none, so without this the console could provision, rename and
 * suspend an organisation but not give anybody a way in.
 *
 * Listing, revoking and restoring an organisation's members is the support
 * panel's job (`domains/platform/support`), through the platform-scope
 * membership routes; a console admin still holds no org role.
 */
export function SeatMemberPanel({ slug }: { slug: string }) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>(SEAT_ROLES[0].value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        const membership = await seatMembership(slug, { email: email.trim(), role });
        toast.success(
          `${email.trim()} seated as ${role}`,
          membership.invited
            ? "They have no account yet, so they have been emailed a link to choose a password."
            : "They already had an account and can sign in now.",
        );
        setEmail("");
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [slug, email, role, toast],
  );

  return (
    <Section
      title="Seat an administrator"
      description="For a new organisation with nobody in it yet."
    >
      <Card padding="md">
        <form onSubmit={submit} className="flex max-w-lg flex-col gap-3">
          {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

          <Input
            type="email"
            label="Email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
            hint="An address with no account is invited: the backend emails a link to set a password. No password passes through this console."
          />

          <label className="flex flex-col gap-1.5">
            <span className="text-osce-meta font-medium text-osce-ink-700">Role</span>
            <select
              value={role}
              onChange={(event) => setRole(event.target.value)}
              disabled={busy}
              className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
            >
              {SEAT_ROLES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !email.trim()}>
              {busy ? "Seating…" : "Seat member"}
            </Button>
          </div>
        </form>
      </Card>
    </Section>
  );
}
