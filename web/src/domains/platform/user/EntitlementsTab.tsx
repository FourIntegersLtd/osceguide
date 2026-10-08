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
  Row,
  RowList,
  Select,
} from "@/foundation/ui";
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
import { humanise } from "@/foundation/format";
import { asContractDate, formatDay } from "@/domains/platform/support";

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
        <Panel
          title="Access"
          description="Everything this person has been given access to, current or ended, oldest first."
          padding="none"
        >
          <AsyncBoundary
            state={state}
            isEmpty={(page) => page.items.length === 0}
            empty={{
              title: "No grants",
              description: "Only the free trial, if any of it is left.",
              bare: true,
            }}
          >
            {(page) => (
              <RowList flush>
                {page.items.map((grant) => (
                  <EntitlementRow
                    key={grant.id}
                    grant={grant}
                    onChanged={state.reload}
                  />
                ))}
              </RowList>
            )}
          </AsyncBoundary>
        </Panel>
      }
      rail={
        <GrantPanel
          userId={userId}
          examCode={examCode}
          onGranted={state.reload}
        />
      }
    />
  );
}

function EntitlementRow({
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
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-osce-data font-medium text-ink">
          {grant.exam_code} · {humanise(grant.source)}
        </p>
        <p className="text-osce-meta text-ink-subtle">
          {formatDay(grant.starts_at)} →{" "}
          {grant.ends_at ? formatDay(grant.ends_at) : "open-ended"}
          {grant.revoked_at ? ` · revoked ${formatDay(grant.revoked_at)}` : ""}
          {grant.source_ref ? ` · ${grant.source_ref}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={grant.live ? "success" : "neutral"}>
          {grant.live ? "Live" : grant.revoked_at ? "Revoked" : "Not live"}
        </Badge>
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
    </Row>
  );
}

function GrantPanel({
  userId,
  examCode,
  onGranted,
}: {
  userId: string;
  examCode?: string | null;
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
