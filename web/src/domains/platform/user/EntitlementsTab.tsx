"use client";

import { useCallback, useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import {
  extendEntitlement,
  grantEntitlement,
  listUserEntitlements,
  revokeEntitlement,
  type PlatformEntitlement,
} from "@/domains/platform/support/api";
import { Row, RowList, Section } from "@/domains/platform/chrome";
import { InlineAction } from "@/domains/platform/user/InlineAction";
import { asContractDate, formatDay } from "@/domains/platform/support";

/**
 * Every grant this person has held, and the three things support may do.
 *
 * Revoked and expired rows are kept on purpose: "your access ended on the
 * 3rd" is the answer most tickets are looking for. A grant made here is
 * source `admin`, which the backend has always allowed and no screen ever
 * wrote; the reason goes in the audit row, not in a chat somewhere.
 */
export function EntitlementsTab({ userId, examCode }: { userId: string; examCode?: string | null }) {
  const state = useAsync((signal) => listUserEntitlements(userId, signal), [userId]);

  return (
    <div className="flex flex-col gap-8">
      <Section title="Access" description="Every grant, live or not, newest last.">
        <AsyncBoundary
          state={state}
          isEmpty={(page) => page.items.length === 0}
          empty={{ title: "No grants", description: "Only the free trial, if any of it is left." }}
        >
          {(page) => (
            <RowList>
              {page.items.map((grant) => (
                <EntitlementRow key={grant.id} grant={grant} onChanged={state.reload} />
              ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Section>
      <GrantPanel userId={userId} examCode={examCode} onGranted={state.reload} />
    </div>
  );
}

function EntitlementRow({ grant, onChanged }: { grant: PlatformEntitlement; onChanged: () => void }) {
  const toast = useToast();
  const [endsAt, setEndsAt] = useState(grant.ends_at ? grant.ends_at.slice(0, 10) : "");

  return (
    <Row className="flex-col items-stretch sm:flex-row sm:items-center">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-ink">
          {grant.exam_code} · {grant.source.replace(/_/g, " ")}
        </p>
        <p className="text-xs text-ink-subtle">
          {formatDay(grant.starts_at)} → {grant.ends_at ? formatDay(grant.ends_at) : "open-ended"}
          {grant.revoked_at ? ` · revoked ${formatDay(grant.revoked_at)}` : ""}
          {grant.source_ref ? ` · ${grant.source_ref}` : ""}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={grant.live ? "success" : "neutral"}>{grant.live ? "Live" : grant.revoked_at ? "Revoked" : "Not live"}</Badge>
        {grant.revoked_at ? null : (
          <>
            <InlineAction
              label="Extend"
              confirmLabel="Save end date"
              requireReason={false}
              reasonLabel="Note"
              onConfirm={async (note) => {
                await extendEntitlement(grant.id, { endsAt: asContractDate(endsAt), note: note || null });
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
        await grantEntitlement(userId, { examCode: code.trim(), endsAt: asContractDate(endsAt), note: note.trim() });
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
    <Section
      title="Grant access"
      description="For a payment taken under another address, a sponsor's seat, or a goodwill month. A purchase that failed to apply is replayed from Billing instead."
    >
      <Card padding="md">
        <form onSubmit={submit} className="flex max-w-lg flex-col gap-3">
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <Input label="Exam code" value={code} onChange={(event) => setCode(event.target.value)} disabled={busy} required />
          <Input
            type="date"
            label="Access ends"
            value={endsAt}
            onChange={(event) => setEndsAt(event.target.value)}
            disabled={busy}
            hint="Leave empty for open-ended."
          />
          <Input label="Why" value={note} onChange={(event) => setNote(event.target.value)} disabled={busy} required hint="Goes in the audit log." />
          <div className="flex justify-end">
            <Button type="submit" disabled={busy || !code.trim() || !note.trim()}>
              {busy ? "Granting…" : "Grant"}
            </Button>
          </div>
        </form>
      </Card>
    </Section>
  );
}
