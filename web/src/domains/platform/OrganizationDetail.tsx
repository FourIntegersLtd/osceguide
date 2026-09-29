"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { LuArrowLeft } from "react-icons/lu";
import { Alert, AsyncBoundary, Button, Card } from "@/foundation/ui";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  listAllOrganizations,
  readOrganization,
  restoreOrganization,
  suspendOrganization,
  type Organization,
} from "@/domains/platform/api";
import { Section, StatusBadge } from "@/domains/platform/chrome";
import { OrganizationSettings } from "@/domains/platform/OrganizationSettings";
import { SeatMemberPanel } from "@/domains/platform/SeatMemberPanel";
import { MembersSection } from "@/domains/platform/MembersSection";
import { AuditSection } from "@/domains/platform/AuditSection";
import { SsoSection } from "@/domains/platform/SsoSection";
import { renewContract } from "@/domains/platform/support/api";
import { asContractDate } from "@/domains/platform/support";
import { Input } from "@/foundation/ui";
import { STATUS_HELP, formatDay, permitsSignIn } from "@/domains/platform/support";

/**
 * One organisation, from the outside.
 *
 * The retiring screen also showed four counts and a delete. The counts stay
 * unread: they need per-org activity counters the platform does not aggregate
 * (see the staff overview's own gap). The member list and the tenant's audit
 * log, which the first cut of this comment said to wait for, are served by
 * dedicated platform routes and rendered below. Delete does not exist — a
 * tenant's rows include candidate results that have to stay defensible.
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
              <PlatformPageHeader
                title={current.name}
                description={`/${current.slug} · ${current.org_type} · created ${formatDay(current.created_at)}`}
                actions={<StatusBadge status={current.status} />}
              />

              {current.parent_org_id ? <ParentOrganization parentId={current.parent_org_id} /> : null}

              <Lifecycle
                organization={current}
                onChanged={(updated) => {
                  setFresh(updated);
                  state.reload();
                }}
              />

              <OrganizationSettings organization={current} onChanged={setFresh} />

              <RenewPanel organization={current} onChanged={(u) => { setFresh(u); state.reload(); }} />

              <SeatMemberPanel slug={current.slug} />

              <MembersSection slug={current.slug} />

              <AuditSection slug={current.slug} />

              <SsoSection slug={current.slug} />
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/**
 * The organisation this one sits under. Read-only: nothing in the console
 * sets a parent yet.
 *
 * The parent arrives as an id, and there is no read of an organisation by id,
 * so its name is found in the directory. Loaded only when there is a parent.
 */
function ParentOrganization({ parentId }: { parentId: string }) {
  const { hrefFor } = useSurface();
  const directory = useAsync((signal) => listAllOrganizations(null, signal), []);
  return (
    <AsyncBoundary state={directory} loading={null}>
      {(organizations) => {
        const parent = organizations.find((item) => item.id === parentId);
        return (
          <p className="-mt-4 text-sm text-ink-muted">
            Part of{" "}
            {parent ? (
              <Link
                href={hrefFor(`/organizations/${encodeURIComponent(parent.slug)}`)}
                className="font-medium text-accent hover:text-accent-hover"
              >
                {parent.name}
              </Link>
            ) : (
              <span className="font-mono">{parentId}</span>
            )}
          </p>
        );
      }}
    </AsyncBoundary>
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


/** A renewal in one step: the dates, and the suspension lifted with them. */
function RenewPanel({ organization, onChanged }: { organization: Organization; onChanged: (u: Organization) => void }) {
  const toast = useToast();
  const [endsAt, setEndsAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const renew = useCallback(async () => {
    const ends = asContractDate(endsAt);
    if (!ends) return;
    setBusy(true);
    setError(null);
    try {
      onChanged(await renewContract(organization.slug, { endsAt: ends }));
      toast.success("Contract renewed", "Any suspension has been lifted.");
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  }, [endsAt, organization.slug, onChanged, toast]);
  return (
    <Section title="Renew" description="New end date, and access restored with it — one step, so the second is not forgotten.">
      <Card padding="md">
        <div className="flex max-w-lg flex-col gap-3">
          {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
          <Input type="date" label="Contract now ends" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} disabled={busy} />
          <div className="flex justify-end">
            <Button disabled={busy || !endsAt} onClick={() => void renew()}>{busy ? "Renewing…" : "Renew"}</Button>
          </div>
        </div>
      </Card>
    </Section>
  );
}
