"use client";

import { useCallback, useState } from "react";
import { ActionRail, Alert, Button, ConfirmModal, Input } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { restoreOrganization, suspendOrganization, type Organization } from "@/domains/platform/api";
import { renewContract } from "@/domains/platform/support/api";
import { asContractDate, contractDatesError, localDay, permitsSignIn, renewalDateError } from "@/domains/platform/support";

/**
 * Renew, then the one lever over access past the divider.
 *
 * Suspending blocks every member's sign-in and keeps every row. Restoring puts
 * the status to `active`, not back to whatever it was — which matters for a
 * tenant that was on trial.
 */
export function OrganizationActions({
  organization,
  onChanged,
}: {
  organization: Organization;
  onChanged: (updated: Organization) => void;
}) {
  const toast = useToast();
  const [endsAt, setEndsAt] = useState("");
  const [busy, setBusy] = useState<"renew" | "access" | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [confirmingSuspend, setConfirmingSuspend] = useState(false);
  const suspended = !permitsSignIn(organization.status);
  // Renewing sets the end date, so it may not fall before the stored start, nor in the past.
  const orderError =
    contractDatesError("", endsAt, {
      startsAt: organization.contract_starts_at?.slice(0, 10) ?? "",
      endsAt: "",
    }) ?? renewalDateError(endsAt, localDay());

  const run = useCallback(
    async (
      kind: "renew" | "access",
      action: () => Promise<Organization>,
      done: string,
      detail?: string,
    ) => {
      setBusy(kind);
      setError(null);
      try {
        onChanged(await action());
        toast.success(done, detail);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(null);
      }
    },
    [onChanged, toast],
  );

  const renew = () => {
    const ends = asContractDate(endsAt);
    if (!ends) return;
    void run(
      "renew",
      () => renewContract(organization.slug, { endsAt: ends }),
      "Contract renewed",
      "Any suspension has been lifted.",
    );
  };

  const toggleAccess = () => {
    if (suspended) void changeAccess();
    else setConfirmingSuspend(true);
  };

  const changeAccess = () =>
    run(
      "access",
      () =>
        suspended
          ? restoreOrganization(organization.slug)
          : suspendOrganization(organization.slug),
      suspended ? "Access restored" : "Access suspended",
    );

  return (
    <ActionRail
      danger={
        <>
          <ConfirmModal
            isOpen={confirmingSuspend}
            onCancel={() => setConfirmingSuspend(false)}
            onConfirm={async () => {
              await changeAccess();
              setConfirmingSuspend(false);
            }}
            isLoading={busy === "access"}
            tone="danger"
            title={`Suspend ${organization.name}?`}
            confirmText="Suspend access"
            message="Every member is locked out at once, including anyone in a sitting that is running now: their circuit stops mid-examination. Nothing is deleted, and Restore access reverses it."
          />
          <Button
            variant={suspended ? "secondary" : "danger"}
            disabled={busy !== null}
            onClick={toggleAccess}
          >
            {busy === "access"
              ? "Working…"
              : suspended
                ? "Restore access"
                : "Suspend access"}
          </Button>
          <p className="text-osce-meta text-ink-subtle">
            {suspended
              ? "Restoring makes the organisation active, even if it was on a trial before. A lapsed contract end date is cleared, so the contract is open-ended until you renew."
              : "Members can still sign in but cannot open the organisation. Nothing is deleted."}
          </p>
        </>
      }
    >
      {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
      <Input
        type="date"
        label="Renew until"
        value={endsAt}
        onChange={(event) => setEndsAt(event.target.value)}
        disabled={busy !== null}
        error={orderError}
        hint="Sets the new end date and lifts any suspension in one step."
      />
      <Button disabled={busy !== null || !endsAt || orderError !== null} onClick={renew}>
        {busy === "renew" ? "Renewing…" : "Renew contract"}
      </Button>
    </ActionRail>
  );
}
