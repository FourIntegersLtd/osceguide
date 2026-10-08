"use client";

import { useState } from "react";
import { Alert, Button, Input, Panel, Select } from "@/foundation/ui";
import {
  IssuedPassword,
  TemporaryPasswordField,
  temporaryPasswordReady,
} from "@/foundation/ui/TemporaryPassword";
import { errorMessage, useToast } from "@/foundation/hooks";
import { seatMembership } from "@/domains/platform/api";
import { ROLE_DESCRIPTIONS, roleLabel } from "@/foundation/session/roles";
import { SEAT_ROLES, humanise, rolesForOrgType } from "@/domains/platform/support";

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
 *
 * The temporary-password option exists because the invitation email cannot
 * always be delivered (an unverified sender domain, say). The admin types a
 * password and relays it by hand; it applies only to a brand-new account and
 * must be changed at first sign-in.
 */
export function SeatMemberPanel({
  slug,
  orgType,
  onSeated,
}: {
  slug: string;
  orgType: string;
  /** Called once someone is seated, so the members list beside this shows them. */
  onSeated: () => void;
}) {
  const toast = useToast();
  const roles = rolesForOrgType(SEAT_ROLES, orgType);
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<string>(
    roles.find((value) => value === "institution_admin") ?? roles[0] ?? SEAT_ROLES[0],
  );
  const [handPassword, setHandPassword] = useState(false);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [issued, setIssued] = useState<{ email: string; password: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const relayed = handPassword && temporaryPassword.length > 0;
      const address = email.trim();
      const membership = await seatMembership(slug, {
        email: email.trim(),
        role,
        ...(relayed ? { temporaryPassword } : {}),
      });
      // `temporary_password_applied` is on the response but not yet in the generated type.
      const applied = (membership as { temporary_password_applied?: boolean }).temporary_password_applied === true;
      setIssued(applied ? { email: address, password: temporaryPassword } : null);
      toast.success(
        `${address} added as ${roleLabel(role, humanise(role)).toLowerCase()}`,
        membership.invited
          ? "They have no account yet, so they have been emailed a link to choose a password."
          : applied
            ? "They can sign in with the password shown below and must change it first."
            : relayed
              ? "They already had an account, so the password you typed was not used. They sign in as before."
              : "They already had an account and can sign in now.",
      );
      setEmail("");
      setTemporaryPassword("");
      setHandPassword(false);
      onSeated();
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel
      title="Add an admin"
      description="For a new organisation with nobody in it yet. Someone without an account is emailed a link to choose a password. If that email cannot reach them, set a temporary one to relay by hand."
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
        {issued ? (
          <IssuedPassword
            email={issued.email}
            password={issued.password}
            onDismiss={() => setIssued(null)}
          />
        ) : null}
        <div className="grid items-end gap-3 sm:grid-cols-[minmax(0,1fr)_14rem_auto]">
          <Input
            type="email"
            label="Email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={busy}
          />
          <Select
            label="Role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            hint={ROLE_DESCRIPTIONS[role]}
            disabled={busy}
          >
            {roles.map((value) => (
              <option key={value} value={value}>
                {roleLabel(value, humanise(value))}
              </option>
            ))}
          </Select>
          <Button
            type="submit"
            disabled={
              busy ||
              !email.trim() ||
              !temporaryPasswordReady(handPassword, temporaryPassword)
            }
          >
            {busy ? "Adding…" : "Add admin"}
          </Button>
        </div>
        <TemporaryPasswordField
          enabled={handPassword}
          onEnabledChange={setHandPassword}
          value={temporaryPassword}
          onChange={setTemporaryPassword}
          disabled={busy}
        />
      </form>
    </Panel>
  );
}
