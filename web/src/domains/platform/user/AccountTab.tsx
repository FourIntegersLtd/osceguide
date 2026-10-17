"use client";

import { useCallback, useState } from "react";
import {
  ActionRail,
  Alert,
  Badge,
  Button,
  ConfirmModal,
  DetailLayout,
  FactList,
  Panel,
  B2CGroupedRow,
  B2CGroupedSection,
} from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import {
  setPlatformAdmin,
  updateUser,
  type DirectoryUser,
  type PlatformUserDetail,
} from "@/domains/platform/api";
import { roleLabel } from "@/foundation/session/roles";
import { formatDay, formatSince } from "@/domains/platform/support";
import { ReissuePasswordPanel } from "@/domains/platform/user/ReissuePasswordPanel";
import { ResetMfaButton } from "@/domains/platform/user/ResetMfaButton";
import {
  accessLabel,
  accessOf,
  accessTone,
  planLabel,
} from "@/domains/platform/users/vocabulary";

/**
 * The account itself: what it paid for and can open, where it belongs, and
 * the two switches — the console and the account.
 *
 * Paid and access are read from what actually happened — a payment, a live
 * grant — and changed where they are recorded: Billing and Entitlements. A
 * flag with nothing behind it is how "paid" and "has access" came apart in the
 * retiring console.
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
          status === "deactivated"
            ? "Account deactivated"
            : "Account reactivated",
          status === "deactivated"
            ? "They are signed out everywhere, any consultation they had open is ended, and they cannot sign in again."
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
      toast.success(
        pending ? "Console access granted" : "Console access revoked",
      );
      setPending(null);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [pending, user, onChanged, toast]);

  const access = facts ? accessOf(facts) : null;
  const liveCodes = facts?.live_exam_codes ?? [];
  // The fields the api sends for a membership here; until the schema is regenerated.
  const memberships = (user.memberships ?? []) as (NonNullable<PlatformUserDetail["memberships"]>[number] & {
    org_name?: string | null;
    org_slug?: string | null;
  })[];

  return (
    <>
      <DetailLayout
        main={
          <>
            {error && !confirmOff && pending === null ? (
              <Alert tone="danger">{error}</Alert>
            ) : null}
            <Panel
              title="Payment and access"
              description="What they have paid for and can use. Make changes on the Billing and Access tabs."
              actions={
                <>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onOpenTab("entitlements")}
                  >
                    Entitlements
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onOpenTab("billing")}
                  >
                    Billing
                  </Button>
                </>
              }
            >
              <FactList
                items={[
                  {
                    label: "Payment",
                    value: access ? (
                      <Badge tone={accessTone(access)}>
                        {accessLabel(access)}
                      </Badge>
                    ) : (
                      "-"
                    ),
                  },
                  { label: "Last paid", value: formatDay(facts?.last_paid_at) },
                  {
                    label: "Plan",
                    value: facts?.has_paid
                      ? planLabel(facts.plan_code)
                      : "None bought",
                  },
                  {
                    label: "Access",
                    value:
                      liveCodes.length > 0
                        ? `${liveCodes.map((code) => code.toUpperCase()).join(", ")} · ${
                            facts?.access_ends_at
                              ? `until ${formatDay(facts.access_ends_at)}`
                              : "open-ended"
                          }`
                        : "No live access",
                  },
                  {
                    // When they last signed in, not whether a session is open:
                    // "Now" for any unexpired refresh chain read as "online".
                    label: "Last signed in",
                    value: facts ? formatSince(facts.last_login_at) : "-",
                  },
                ]}
              />
            </Panel>

            {user.must_change_password ? (
              <ReissuePasswordPanel userId={user.id} email={user.email} />
            ) : null}

            <B2CGroupedSection eyebrow="Memberships">
              {memberships.length === 0 ? (
                <B2CGroupedRow title="No memberships" meta="This account belongs to no organisation." />
              ) : (
                memberships.map((membership) => (
                  <B2CGroupedRow
                    key={membership.id}
                    title={membership.org_name ?? membership.org_slug ?? "Organisation"}
                    meta={`${roleLabel(membership.role)}${
                      membership.product_surface ? ` · ${membership.product_surface}` : ""
                    }${membership.invited ? " · invited, not signed in" : ""}`}
                    trailing={
                      <Badge dot tone={membership.status === "active" ? "success" : "neutral"}>
                        {membership.status}
                      </Badge>
                    }
                  />
                ))
              )}
            </B2CGroupedSection>
          </>
        }
        rail={
          <ActionRail
            title="Account"
            danger={
              <>
                <Button
                  variant={deactivated ? "primary" : "danger"}
                  disabled={busy}
                  onClick={() =>
                    deactivated ? void setStatus("active") : setConfirmOff(true)
                  }
                >
                  {busy
                    ? "Working…"
                    : deactivated
                      ? "Reactivate account"
                      : "Deactivate account"}
                </Button>
                <p className="text-osce-meta text-ink-subtle">
                  {deactivated
                    ? "Deactivated. They have been signed out everywhere and cannot sign in."
                    : "Signs them out everywhere. Nothing is deleted."}
                </p>
              </>
            }
          >
            <p className="text-osce-meta text-ink-subtle">
              {user.is_platform_admin
                ? "May open every organisation in this console."
                : "No platform administrator access."}
            </p>
            <Button
              variant="secondary"
              onClick={() => setPending(!user.is_platform_admin)}
            >
              {user.is_platform_admin ? "Revoke console" : "Grant console"}
            </Button>
            <ResetMfaButton userId={user.id} email={user.email} />
          </ActionRail>
        }
      />

      <ConfirmModal
        isOpen={confirmOff}
        onCancel={() => setConfirmOff(false)}
        onConfirm={() => setStatus("deactivated")}
        isLoading={busy}
        error={error}
        tone="danger"
        title="Deactivate this account?"
        confirmText="Deactivate"
        message={`${user.email} will be signed out everywhere and refused until reactivated. Any consultation they have open is ended. Nothing is deleted, and their organisation roles stay as they are. An organisation's only active administrator cannot be deactivated.`}
      />
      <ConfirmModal
        isOpen={pending !== null}
        onCancel={() => {
          setPending(null);
          setError(null);
        }}
        onConfirm={() => confirmConsole()}
        isLoading={busy}
        error={error}
        tone={pending === false ? "danger" : "default"}
        title={
          pending ? "Grant the staff console?" : "Revoke the staff console?"
        }
        confirmText={pending ? "Grant" : "Revoke"}
        message={
          pending
            ? `${user.email} will be able to see and change every organisation on the platform.`
            : `${user.email} will lose this console. Their organisation memberships are untouched.`
        }
      />
    </>
  );
}
