"use client";

import { useCallback, useState } from "react";
import { Alert, Badge, Button, Card, ConfirmModal } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { setPlatformAdmin, updateUser, type DirectoryUser, type PlatformUserDetail } from "@/domains/platform/api";
import { formatDay } from "@/domains/platform/support";
import { accessLabel, accessOf, accessTone, planLabel } from "@/domains/platform/users/vocabulary";

/**
 * The retiring console's "Account status" card.
 *
 * Its Paid / Unpaid and Active / Inactive buttons flipped flags on the user
 * document, and a flag with nothing behind it is how "paid" and "has access"
 * came apart. Here both are read from what actually happened — a payment, a
 * live grant — and changed where they are recorded: Billing and Entitlements.
 * What this tab does change is the account itself: off, and the console.
 */
export function AccountTab({
  user,
  facts,
  onChanged,
  onOpenTab,
}: {
  user: PlatformUserDetail;
  facts: DirectoryUser | null;
  onChanged: (user: PlatformUserDetail) => void;
  onOpenTab: (tab: "billing" | "entitlements") => void;
}) {
  const toast = useToast();
  const [pending, setPending] = useState<boolean | null>(null);
  const [confirmOff, setConfirmOff] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deactivated = user.status === "deactivated";

  const setStatus = useCallback(
    async (status: "active" | "deactivated") => {
      setBusy(true);
      setError(null);
      try {
        onChanged(await updateUser(user.id, { status }));
        toast.success(
          status === "deactivated" ? "Account deactivated" : "Account reactivated",
          status === "deactivated"
            ? "Their sessions have ended and their token is refused from now on."
            : "They can sign in again.",
        );
        setConfirmOff(false);
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setBusy(false);
      }
    },
    [user.id, onChanged, toast],
  );

  const confirmConsole = useCallback(async () => {
    if (pending === null) return;
    setBusy(true);
    setError(null);
    try {
      await setPlatformAdmin(user.id, pending);
      onChanged({ ...user, is_platform_admin: pending });
      toast.success(pending ? "Console access granted" : "Console access revoked");
      setPending(null);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [pending, user, onChanged, toast]);

  const access = facts ? accessOf(facts) : null;

  return (
    <div className="flex flex-col gap-4">
      {error ? <Alert tone="danger">{error}</Alert> : null}

      <Card padding="md" title="Payment and access" description="Read from what happened. Changed where it is recorded.">
        <dl className="grid grid-cols-[auto_1fr] items-center gap-x-4 gap-y-2 text-osce-data">
          <dt className="text-ink-muted">Payment</dt>
          <dd>
            {access ? <Badge tone={accessTone(access)}>{accessLabel(access)}</Badge> : <span className="text-ink-subtle">—</span>}
            {facts?.last_paid_at ? <span className="ml-2 text-osce-meta text-ink-subtle">last paid {formatDay(facts.last_paid_at)}</span> : null}
          </dd>
          <dt className="text-ink-muted">Plan</dt>
          <dd className="text-ink">{facts?.has_paid ? planLabel(facts.plan_code) : "None bought"}</dd>
          <dt className="text-ink-muted">Access</dt>
          <dd className="text-ink">
            {facts && (facts.live_exam_codes ?? []).length > 0
              ? `${(facts.live_exam_codes ?? []).map((code) => code.toUpperCase()).join(", ")} · ${
                  facts.access_ends_at ? `until ${formatDay(facts.access_ends_at)}` : "open-ended"
                }`
              : "No live access"}
          </dd>
          <dt className="text-ink-muted">Signed in</dt>
          <dd className="text-ink">{facts ? (facts.signed_in ? "Now" : "No") : "—"}</dd>
        </dl>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => onOpenTab("entitlements")}>
            Grant, extend or revoke access
          </Button>
          <Button variant="secondary" size="sm" onClick={() => onOpenTab("billing")}>
            Record a payment or refund
          </Button>
        </div>
      </Card>

      <Card padding="md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="min-w-0 text-osce-data text-ink-muted">
            {deactivated
              ? "This account is deactivated. Its sessions have ended and its token is refused."
              : "This account is active."}
          </p>
          <Button
            variant={deactivated ? "primary" : "danger"}
            size="sm"
            disabled={busy}
            onClick={() => (deactivated ? void setStatus("active") : setConfirmOff(true))}
          >
            {busy ? "Working…" : deactivated ? "Reactivate" : "Deactivate"}
          </Button>
        </div>
      </Card>

      <Card padding="md">
        <p className="text-osce-data text-ink-muted">
          {user.is_platform_admin
            ? `${user.email} may open every organisation in this console.`
            : `${user.email} does not have platform administrator access.`}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {user.is_platform_admin ? (
            <Button variant="secondary" size="sm" onClick={() => setPending(false)}>
              Revoke console
            </Button>
          ) : (
            <Button variant="secondary" size="sm" onClick={() => setPending(true)}>
              Grant console
            </Button>
          )}
        </div>
      </Card>

      <ConfirmModal
        isOpen={confirmOff}
        onCancel={() => setConfirmOff(false)}
        onConfirm={() => void setStatus("deactivated")}
        isLoading={busy}
        error={error}
        tone="danger"
        title="Deactivate this account?"
        confirmText="Deactivate"
        message={`${user.email} will be signed out everywhere and refused until reactivated. Nothing is deleted.`}
      />
      <ConfirmModal
        isOpen={pending !== null}
        onCancel={() => {
          setPending(null);
          setError(null);
        }}
        onConfirm={() => void confirmConsole()}
        isLoading={busy}
        error={error}
        tone={pending === false ? "danger" : "default"}
        title={pending ? "Grant the staff console?" : "Revoke the staff console?"}
        confirmText={pending ? "Grant" : "Revoke"}
        message={
          pending
            ? `${user.email} will be able to see and change every organisation on the platform.`
            : `${user.email} will lose this console. Their organisation memberships are untouched.`
        }
      />
    </div>
  );
}
