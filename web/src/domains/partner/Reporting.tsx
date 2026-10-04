"use client";

import { useCallback, useState } from "react";
import { LuMail, LuPlus } from "react-icons/lu";
import { Alert, AsyncBoundary, Button, EmptyState, Input, B2CPageHeader, Panel } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import {
  addPartnerReporter,
  listPartnerRefIds,
  type TrackingPage,
} from "@/capabilities/staff-growth/api";

/**
 * The links a partner publishes, and who may read the numbers.
 *
 * Each tracking reference is a separate campaign — a journal article, a
 * newsletter, a conference — so they are listed rather than summed. The funnel
 * on the overview is the sum; this is where a partner sees which of their
 * placements actually worked.
 */
export function PartnerReporting({ partner }: { partner: string }) {
  const { session } = useSession();
  const refIds = useAsync((signal) => listPartnerRefIds(partner, signal), [partner]);
  /*
   * A reporter is appointed by OSCE Guide staff, not by the partner — the
   * backend route is platform-admin only ("partners do not appoint their own
   * reporters"). The form used to render for every partner team member and
   * 403 on submit; this reads the same permission the backend checks rather
   * than repeating that discovery for each of them.
   */
  const canAddReporter = can(session, "administer_platform");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Reporting"
        subtitle="Your tracking references, and who can see the numbers."
      />
      <AsyncBoundary state={refIds}>{(data) => <RefIds data={data} />}</AsyncBoundary>
      {canAddReporter ? (
        <AddReporter partner={partner} />
      ) : (
        <Panel title="Who can read this">
          <p className="text-sm text-ink-muted">
            A reporter sees these numbers and nothing else. Ask OSCE Guide staff to add someone. Reporters are added by us, not by your team.
          </p>
        </Panel>
      )}
    </div>
  );
}

function RefIds({ data }: { data: TrackingPage }) {
  const items = data.items ?? [];

  return (
    <Panel title="Tracking references">
      {items.length === 0 ? (
        <EmptyState
          title="No references yet"
          description="A reference appears here the first time somebody arrives through one of your links."
        />
      ) : (
        <ul className="divide-y divide-border">
          {items.map((item) => (
            <li key={item.ref_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-ink">{item.ref_id}</p>
                <p className="truncate text-xs text-ink-subtle">
                  {item.exam_code.toUpperCase()} · {item.landing_path}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function AddReporter({ partner }: { partner: string }) {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [added, setAdded] = useState<string | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await addPartnerReporter(partner, email);
        setAdded(email);
        setEmail("");
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [partner, email],
  );

  return (
    <Panel
      title="Who can read this"
      description="A reporter sees these numbers and nothing else. They are not given access to the platform’s content or to any candidate’s work."
    >
      <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
        <div className="min-w-56 flex-1">
          <Input
            label="Email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={busy || email.trim() === ""} isLoading={busy}>
          <LuPlus className="h-4 w-4" aria-hidden /> Add reporter
        </Button>
      </form>
      {error && (
        <Alert tone="danger" className="mt-3">
          {errorMessage(error)}
        </Alert>
      )}
      {added && !error && (
        <Alert tone="success" className="mt-3">
          <LuMail className="mr-1.5 inline h-4 w-4" aria-hidden />
          {added} can now read your reporting.
        </Alert>
      )}
    </Panel>
  );
}
