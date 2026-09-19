"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { LuArrowLeft } from "react-icons/lu";
import { Alert, AsyncBoundary, Button, Card, PageHeader } from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  readOrganization,
  restoreOrganization,
  suspendOrganization,
  type Organization,
} from "@/domains/platform/api";
import { Section, StatusBadge } from "@/domains/platform/chrome";
import { OrganizationSettings } from "@/domains/platform/OrganizationSettings";
import { SeatMemberPanel } from "@/domains/platform/SeatMemberPanel";
import { STATUS_HELP, formatDay, permitsSignIn } from "@/domains/platform/support";

/**
 * One organisation, from the outside.
 *
 * The retiring screen also showed four counts, a member list, the tenant's
 * audit log and a delete. None of the four are this console's to read: a
 * platform admin may *read* an organisation for support and inherits none of
 * its powers, so the memberships list and the audit log — both `OrgAdmin` on
 * the backend — answer 403 here. Delete does not exist at all, and that is a
 * decision: a tenant's rows include candidate results that have to stay
 * defensible. All four are in `docs/port-gaps.md`.
 *
 * The read itself is `GET /orgs/{slug}`, not a platform route — there is no
 * `GET /platform/organizations/{slug}`, and the org-scoped read admits a
 * platform admin on purpose.
 */
export function OrganizationDetail({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readOrganization(slug, signal), [slug]);
  const [fresh, setFresh] = useState<Organization | null>(null);

  const organization = fresh ?? state.data;

  return (
    <div className="flex flex-col gap-8">
      <div>
        <Link
          href={hrefFor("/organizations")}
          className="inline-flex items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
        >
          <LuArrowLeft className="h-4 w-4" aria-hidden /> Organisations
        </Link>
      </div>

      <AsyncBoundary state={state}>
        {(loaded) => {
          const current = organization ?? loaded;
          return (
            <>
              <PageHeader
                title={current.name}
                description={`/${current.slug} · ${current.org_type} · created ${formatDay(current.created_at)}`}
                actions={<StatusBadge status={current.status} />}
              />

              <Lifecycle
                organization={current}
                onChanged={(updated) => {
                  setFresh(updated);
                  state.reload();
                }}
              />

              <OrganizationSettings organization={current} onChanged={setFresh} />

              <SeatMemberPanel slug={current.slug} />

              <Section title="Not visible from here">
                <Card padding="md">
                  <p className="text-sm text-ink-muted">
                    This organisation&rsquo;s member list and its audit log belong to its own
                    administrators. A platform administrator may read an organisation for support
                    and inherits none of its powers, so neither is readable from this console.
                  </p>
                </Card>
              </Section>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/**
 * Suspend and restore: the only lever this console has over access.
 *
 * Suspending blocks every member's sign-in and keeps every row. Restoring puts
 * the organisation back to `active` — note that it does not put back whatever
 * it was before, which matters for a tenant that was on trial.
 */
function Lifecycle({
  organization,
  onChanged,
}: {
  organization: Organization;
  onChanged: (updated: Organization) => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const suspended = !permitsSignIn(organization.status);

  const toggle = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = suspended
        ? await restoreOrganization(organization.slug)
        : await suspendOrganization(organization.slug);
      onChanged(updated);
      toast.success(suspended ? "Access restored" : "Access suspended");
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [suspended, organization.slug, onChanged, toast]);

  return (
    <Section title="Access">
      <Card padding="md">
        <div className="flex flex-col gap-3">
          {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="min-w-0 text-sm text-ink-muted">
              {STATUS_HELP[organization.status] ??
                `Status "${organization.status}". Members cannot sign in.`}
            </p>
            <Button
              variant={suspended ? "primary" : "danger"}
              disabled={busy}
              onClick={() => void toggle()}
            >
              {busy ? "Working…" : suspended ? "Restore access" : "Suspend access"}
            </Button>
          </div>
          {suspended ? (
            <p className="text-xs text-ink-subtle">
              Restoring sets the status to <strong>active</strong>, not back to what it was before.
            </p>
          ) : null}
        </div>
      </Card>
    </Section>
  );
}
