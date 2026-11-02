"use client";

import { useCallback, useState } from "react";
import {
  Alert,
  AsyncBoundary,
  Badge,
  Button,
  DetailLayout,
  Input,
  Panel,
  Select,
} from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { listExams } from "@/capabilities/stations";
import {
  extendEntitlement,
  grantEntitlement,
  listUserEntitlements,
  revokeEntitlement,
  type PlatformEntitlement,
} from "@/domains/platform/support/api";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import { asContractDate, formatDay } from "@/domains/platform/support";
import {
  accessSummary,
  accessUntil,
  coveredByAnother,
  grantState,
  sourceLabel,
  type GrantState,
} from "@/domains/platform/user/grantStatus";

const STATE_BADGE: Record<GrantState, { tone: "success" | "neutral" | "warning"; label: (grant: PlatformEntitlement) => string }> = {
  live: { tone: "success", label: () => "Live" },
  queued: { tone: "warning", label: (grant) => `Starts ${formatDay(grant.starts_at)}` },
  ended: { tone: "neutral", label: () => "Ended" },
  revoked: { tone: "neutral", label: () => "Revoked" },
};

/**
 * Every grant this person has held, and the three things support may do.
 *
 * Revoked and expired rows are kept on purpose: "your access ended on the
 * 3rd" is the answer most tickets are looking for. A grant made here is
 * source `admin`, which the backend has always allowed and no screen ever
 * wrote; the reason goes in the audit row, not in a chat somewhere.
 */
export function EntitlementsTab({
  userId,
  examCode,
}: {
  userId: string;
  examCode?: string | null;
}) {
  const state = useAsync(
    (signal) => listUserEntitlements(userId, signal),
    [userId],
  );

  return (
    <DetailLayout
      main={
        <AsyncBoundary state={state}>
          {(page) => {
            const now = new Date();
            return (
            <Table<PlatformEntitlement>
              rows={page.items}
              themeType="b2b"
              idField="id"
              title="Access"
              description={`${accessSummary(page.items, now)}. Every grant they have held is listed below, oldest first. They have access while any one of them is live.`}
              empty={{ title: "No grants", description: "Only the free trial, if any of it is left." }}
              columns={[
                {
                  header: "Grant",
                  key: "exam_code",
                  priority: "primary",
                  render: (grant) => (
                    <div className="min-w-0">
                      <p className="font-medium text-ink">
                        {grant.exam_code} · {sourceLabel(grant)}
                      </p>
                      <p className="text-osce-meta text-ink-subtle" title={grant.source_ref ?? undefined}>
                        {formatDay(grant.starts_at)} → {grant.ends_at ? formatDay(grant.ends_at) : "open-ended"}
                        {grant.revoked_at ? ` · revoked ${formatDay(grant.revoked_at)}` : ""}
                      </p>
                    </div>
                  ),
                },
                {
                  header: "Status",
                  key: "live",
                  render: (grant) => {
                    const state = grantState(grant, now);
                    return (
                      <div className="flex flex-col items-start gap-1">
                        <Badge dot tone={STATE_BADGE[state].tone}>
                          {STATE_BADGE[state].label(grant)}
                        </Badge>
                        {coveredByAnother(grant, page.items, now) ? (
                          <span className="text-osce-meta text-ink-subtle">Another grant covers this</span>
                        ) : null}
                      </div>
                    );
                  },
                },
                {
                  header: "Actions",
                  key: "id",
                  render: (grant) => <EntitlementActions grant={grant} onChanged={state.reload} />,
                },
              ]}
            />
            );
          }}
        </AsyncBoundary>
      }
      rail={
        <GrantPanel
          userId={userId}
          examCode={examCode}
          existing={state.data?.items ?? []}
          onGranted={state.reload}
        />
      }
    />
  );
}

function EntitlementActions({
  grant,
  onChanged,
}: {
  grant: PlatformEntitlement;
  onChanged: () => void;
}) {
  const toast = useToast();
  const [endsAt, setEndsAt] = useState(
    grant.ends_at ? grant.ends_at.slice(0, 10) : "",
  );

  return (
    <div className="flex flex-wrap items-center gap-2">
      {grant.revoked_at ? null : (
        <>
          <InlineAction
            label="Extend"
            confirmLabel="Save end date"
            requireReason={false}
            reasonLabel="Note"
            onConfirm={async (note) => {
              await extendEntitlement(grant.id, {
                endsAt: asContractDate(endsAt),
                note: note || null,
              });
              toast.success("End date saved");
              onChanged();
            }}
          >
            <Input
              type="date"
              label="Access ends"
              value={endsAt}
              onChange={(event) => setEndsAt(event.target.value)}
              hint="Leave empty for open-ended."
            />
          </InlineAction>
          <InlineAction
            label="Revoke"
            tone="danger"
            onConfirm={async (reason) => {
              await revokeEntitlement(grant.id, reason);
              toast.success("Access revoked");
              onChanged();
            }}
          />
        </>
      )}
    </div>
  );
}

function GrantPanel({
  userId,
  examCode,
  existing,
  onGranted,
}: {
  userId: string;
  examCode?: string | null;
  existing: PlatformEntitlement[];
  onGranted: () => void;
}) {
  const toast = useToast();
  const [code, setCode] = useState(examCode ?? "");
  // The exams that exist, so a typo cannot grant access to nothing. The
  // account's own exam stays a choice even when it is not in the catalogue.
  const exams = useAsync((signal) => listExams(signal), []);
  const examChoices = exams.data?.items ?? [];
  const [endsAt, setEndsAt] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const heldUntil = code ? accessUntil(existing, code, new Date()) : undefined;

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await grantEntitlement(userId, {
          examCode: code.trim(),
          endsAt: asContractDate(endsAt),
          note: note.trim(),
        });
        toast.success(`${code.trim()} granted`);
        setNote("");
        onGranted();
      } catch (cause) {
        setError(errorMessage(cause));
      } finally {
        setBusy(false);
      }
    },
    [userId, code, endsAt, note, toast, onGranted],
  );

  return (
    <Panel
      title="Grant access"
      description="For a payment taken under another address, a sponsor's seat, or a goodwill month. If a purchase did not give access, retry it from the Billing tab instead."
      padding="sm"
    >
      <form onSubmit={submit} className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {exams.error ? (
          <Alert tone="danger">Could not load the exams: {errorMessage(exams.error)}</Alert>
        ) : null}
        <Select
          label="Exam"
          value={code}
          onChange={(event) => setCode(event.target.value)}
          disabled={busy || exams.loading}
          required
        >
          <option value="">{exams.loading ? "Loading exams…" : "Choose an exam"}</option>
          {examCode && !examChoices.some((exam) => exam.code === examCode) ? (
            <option value={examCode}>{examCode.toUpperCase()}</option>
          ) : null}
          {examChoices.map((exam) => (
            <option key={exam.code} value={exam.code}>
              {`${exam.name} (${exam.code})`}
            </option>
          ))}
        </Select>
        {heldUntil !== undefined ? (
          <Alert tone="warning">
            {heldUntil === null
              ? "They already have open-ended access to this exam. A new grant changes nothing today."
              : `They already have access to this exam until ${formatDay(heldUntil.toISOString())}. A grant ending before then changes nothing today.`}
          </Alert>
        ) : null}
        <Input
          type="date"
          label="Access ends"
          value={endsAt}
          onChange={(event) => setEndsAt(event.target.value)}
          disabled={busy}
          hint="Leave empty for open-ended."
        />
        <Input
          label="Why"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          disabled={busy}
          required
          hint="Goes in the audit log."
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={busy || !code.trim() || !note.trim()}>
            {busy ? "Granting…" : "Grant"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}
