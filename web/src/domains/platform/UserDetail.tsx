"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { LuShieldCheck } from "react-icons/lu";
import {
  Alert,
  AsyncBoundary,
  Badge,
  B2CSegmentedTabs,
  Button,
  Card,
  ConfirmModal,
  Input,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  readUser,
  resetUserPassword,
  setPlatformAdmin,
  updateUser,
  type PlatformUserDetail,
} from "@/domains/platform/api";
import { Row, RowList } from "@/domains/platform/chrome";
import { formatDay } from "@/domains/platform/support";
import { AttemptsTab } from "@/domains/platform/user/AttemptsTab";
import { EntitlementsTab } from "@/domains/platform/user/EntitlementsTab";
import { BillingTab } from "@/domains/platform/user/BillingTab";
import { HistoryTab } from "@/domains/platform/user/HistoryTab";

type Tab = "profile" | "attempts" | "entitlements" | "billing" | "access" | "memberships" | "history";

/**
 * The support view of one account.
 *
 * The first three tabs answer the tickets support actually gets — no
 * feedback, no access, paid and nothing happened — and carry the levers that
 * fix them. Access and Memberships are what the console always had; History
 * is the audit log narrowed to this person, so "who did that and when?" is
 * answered on the same screen.
 */
const USER_TABS: B2CSegmentedTabItem<Tab>[] = [
  { id: "profile", label: "Profile" },
  { id: "attempts", label: "Attempts" },
  { id: "entitlements", label: "Entitlements" },
  { id: "billing", label: "Billing" },
  { id: "access", label: "Access" },
  { id: "memberships", label: "Memberships" },
  { id: "history", label: "History" },
];

export function UserDetail({ userId }: { userId: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<Tab>("profile");
  const state = useAsync((signal) => readUser(userId, signal), [userId]);
  const [fresh, setFresh] = useState<PlatformUserDetail | null>(null);
  const user = fresh ?? state.data;

  const tabs: B2CSegmentedTabItem<Tab>[] = USER_TABS;

  return (
    <div className="flex flex-col gap-4">
      <Link
        href={hrefFor("/users")}
        className="inline-flex items-center gap-1 rounded-md text-osce-meta font-medium text-b2c-text-muted hover:text-osce-ink-900 focus:outline-none focus:ring-2 focus:ring-osce-accent/20"
      >
        ← Users
      </Link>

      <AsyncBoundary state={state}>
        {(loaded) => {
          const current = user ?? loaded;
          return (
            <>
              <PlatformPageHeader
                title={current.email}
                description={`${current.name || "No name"} · joined ${formatDay(current.created_at)}`}
                actions={
                  current.is_platform_admin ? (
                    <Badge tone="success">
                      <LuShieldCheck className="mr-1 h-3 w-3" aria-hidden />
                      Platform admin
                    </Badge>
                  ) : null
                }
              />

              <B2CSegmentedTabs
                items={tabs}
                value={tab}
                onChange={setTab}
                aria-label="User detail"
              />

              {tab === "profile" ? (
                <ProfileTab user={current} onSaved={setFresh} />
              ) : null}
              {tab === "access" ? (
                <AccessTab user={current} onChanged={setFresh} />
              ) : null}
              {tab === "memberships" ? <MembershipsTab user={current} /> : null}
              {tab === "attempts" ? <AttemptsTab userId={current.id} /> : null}
              {tab === "entitlements" ? (
                <EntitlementsTab userId={current.id} examCode={current.exam_code} />
              ) : null}
              {tab === "billing" ? <BillingTab userId={current.id} /> : null}
              {tab === "history" ? <HistoryTab userId={current.id} /> : null}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function ProfileTab({
  user,
  onSaved,
}: {
  user: PlatformUserDetail;
  onSaved: (user: PlatformUserDetail) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState(user.name);
  const [examCode, setExamCode] = useState(user.exam_code ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const save = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await updateUser(user.id, {
        name: name.trim() || null,
        exam_code: examCode.trim() || null,
      });
      onSaved(updated);
      toast.success("Profile saved");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [user.id, name, examCode, onSaved, toast]);

  const reset = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      await resetUserPassword(user.id);
      toast.success("Password reset emailed", "If the account exists, they will receive a link.");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }, [user.id, toast]);

  return (
    <Card padding="md">
        <div className="flex max-w-lg flex-col gap-3">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} disabled={busy} />
          <Input
            label="Exam code"
            value={examCode}
            onChange={(e) => setExamCode(e.target.value)}
            disabled={busy}
            hint="Optional default exam for this learner account."
          />
          {user.last_login_at ? (
            <p className="text-xs text-ink-subtle">Last sign-in {formatDay(user.last_login_at)}</p>
          ) : null}
          {user.must_change_password ? (
            <p className="text-xs text-ink-subtle">Must change password on next sign-in.</p>
          ) : null}
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="secondary" disabled={busy} onClick={() => void reset()}>
              Send password reset
            </Button>
            <Button disabled={busy} onClick={() => void save()}>
              {busy ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </Card>
  );
}

function AccessTab({
  user,
  onChanged,
}: {
  user: PlatformUserDetail;
  onChanged: (user: PlatformUserDetail) => void;
}) {
  const toast = useToast();
  const [pending, setPending] = useState<boolean | null>(null);
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
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setBusy(false);
      }
    },
    [user.id, onChanged, toast],
  );

  const confirm = useCallback(async () => {
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

  return (
    <>
      <Card padding="md">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="min-w-0 text-sm text-ink-muted">
            {deactivated
              ? "This account is deactivated. Its sessions have ended and its token is refused."
              : "This account is active."}
          </p>
          <Button
            variant={deactivated ? "primary" : "danger"}
            size="sm"
            disabled={busy}
            onClick={() => void setStatus(deactivated ? "active" : "deactivated")}
          >
            {busy ? "Working…" : deactivated ? "Reactivate" : "Deactivate"}
          </Button>
        </div>
        {error ? (
          <div className="mt-3">
            <Alert tone="danger">{error}</Alert>
          </div>
        ) : null}
      </Card>

      <Card padding="md">
        <p className="text-sm text-ink-muted">
          {user.is_platform_admin
            ? `${user.email} may open every organisation in this console.`
            : `${user.email} does not have platform administrator access.`}
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => setPending(true)}>
            Grant console
          </Button>
          <Button variant="secondary" size="sm" onClick={() => setPending(false)}>
            Revoke console
          </Button>
        </div>
      </Card>

      <ConfirmModal
        isOpen={pending !== null}
        onCancel={() => {
          setPending(null);
          setError(null);
        }}
        onConfirm={() => void confirm()}
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
    </>
  );
}

function MembershipsTab({ user }: { user: PlatformUserDetail }) {
  const memberships = user.memberships ?? [];

  return memberships.length === 0 ? (
    <Card padding="md">
      <p className="text-osce-body text-b2c-text-muted">This account belongs to no organisation.</p>
    </Card>
  ) : (
    <RowList>
          {memberships.map((membership) => (
            <Row key={membership.id}>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">
                  {membership.email ?? membership.user_id}
                </p>
                <p className="truncate text-xs text-ink-subtle">{membership.role}</p>
              </div>
            </Row>
          ))}
        </RowList>
  );
}
