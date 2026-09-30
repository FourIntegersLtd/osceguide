"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import {
  ActionRail,
  Alert,
  AsyncBoundary,
  B2CSegmentedTabs,
  Button,
  DetailLayout,
  FactList,
  Input,
  Panel,
  PlatformPageHeader,
  type B2CSegmentedTabItem,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  listAllOrganizations,
  readOrganization,
  restoreOrganization,
  suspendOrganization,
  type Organization,
} from "@/domains/platform/api";
import { StatusBadge } from "@/domains/platform/chrome";
import { OrganizationSettings } from "@/domains/platform/OrganizationSettings";
import { SeatMemberPanel } from "@/domains/platform/SeatMemberPanel";
import { MembersSection } from "@/domains/platform/MembersSection";
import { AuditSection } from "@/domains/platform/AuditSection";
import { SsoSection } from "@/domains/platform/SsoSection";
import { renewContract } from "@/domains/platform/support/api";
import {
  ORG_TYPES,
  STATUS_HELP,
  asContractDate,
  formatDay,
  permitsSignIn,
} from "@/domains/platform/support";

type Tab = "overview" | "settings" | "members" | "sso" | "audit";

const ORG_TABS: B2CSegmentedTabItem<Tab>[] = [
  { id: "overview", label: "Overview" },
  { id: "settings", label: "Settings" },
  { id: "members", label: "Members" },
  { id: "sso", label: "SSO" },
  { id: "audit", label: "Audit" },
];

/**
 * One organisation, from the outside.
 *
 * Delete does not exist — a tenant's rows include candidate results that have
 * to stay defensible. The read is `GET /orgs/{slug}`, not a platform route:
 * there is no `GET /platform/organizations/{slug}`, and the org-scoped read
 * admits a platform admin on purpose.
 */
export function OrganizationDetail({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const [tab, setTab] = useState<Tab>("overview");
  const state = useAsync((signal) => readOrganization(slug, signal), [slug]);
  const [fresh, setFresh] = useState<Organization | null>(null);

  const organization = fresh ?? state.data;
  const changedAndReload = (updated: Organization) => {
    setFresh(updated);
    state.reload();
  };

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(loaded) => {
          const current = organization ?? loaded;
          return (
            <>
              <PlatformPageHeader
                title={current.name}
                description={`/${current.slug}`}
                back={{
                  href: hrefFor("/organizations"),
                  label: "Organisations",
                }}
                actions={<StatusBadge status={current.status} />}
              />

              <B2CSegmentedTabs
                items={ORG_TABS}
                value={tab}
                onChange={setTab}
                aria-label="Organisation detail"
                className="mb-0 sm:mb-0"
              />

              {tab === "overview" ? (
                <DetailLayout
                  main={<OrganizationFacts organization={current} />}
                  rail={
                    <OrganizationActions
                      organization={current}
                      onChanged={changedAndReload}
                    />
                  }
                />
              ) : null}
              {tab === "settings" ? (
                <OrganizationSettings
                  organization={current}
                  onChanged={setFresh}
                />
              ) : null}
              {tab === "members" ? (
                <div className="flex flex-col gap-6">
                  <SeatMemberPanel slug={current.slug} />
                  <MembersSection slug={current.slug} />
                </div>
              ) : null}
              {tab === "sso" ? <SsoSection slug={current.slug} /> : null}
              {tab === "audit" ? <AuditSection slug={current.slug} /> : null}
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function OrganizationFacts({ organization }: { organization: Organization }) {
  const typeLabel =
    ORG_TYPES.find((type) => type.value === organization.org_type)?.label ??
    organization.org_type;
  const items: { label: string; value: React.ReactNode }[] = [
    {
      label: "Slug",
      value: <span className="font-mono">{organization.slug}</span>,
    },
    { label: "Type", value: typeLabel },
    { label: "Created", value: formatDay(organization.created_at) },
    {
      label: "Access starts",
      value: formatDay(organization.contract_starts_at),
    },
    { label: "Access ends", value: formatDay(organization.contract_ends_at) },
  ];
  if (organization.parent_org_id) {
    items.push({
      label: "Part of",
      value: <ParentName parentId={organization.parent_org_id} />,
    });
  }
  return (
    <Panel title="Organisation">
      <div className="flex flex-col gap-5">
        <p className="text-osce-body text-ink-muted">
          {STATUS_HELP[organization.status] ??
            `Status "${organization.status}". Members cannot sign in.`}
        </p>
        <FactList items={items} />
      </div>
    </Panel>
  );
}

/**
 * The parent arrives as an id and there is no read of an organisation by id,
 * so its name is found in the directory. Loaded only when there is a parent.
 */
function ParentName({ parentId }: { parentId: string }) {
  const { hrefFor } = useSurface();
  const directory = useAsync(
    (signal) => listAllOrganizations(null, signal),
    [],
  );
  return (
    <AsyncBoundary
      state={directory}
      loading={<span className="text-ink-subtle">…</span>}
    >
      {(organizations) => {
        const parent = organizations.find((item) => item.id === parentId);
        return parent ? (
          <Link
            href={hrefFor(`/organizations/${encodeURIComponent(parent.slug)}`)}
            className="font-medium text-accent hover:text-accent-hover"
          >
            {parent.name}
          </Link>
        ) : (
          <span className="font-mono">{parentId}</span>
        );
      }}
    </AsyncBoundary>
  );
}

/**
 * Renew, then the one lever over access past the divider.
 *
 * Suspending blocks every member's sign-in and keeps every row. Restoring puts
 * the status to `active`, not back to whatever it was — which matters for a
 * tenant that was on trial.
 */
function OrganizationActions({
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
  const suspended = !permitsSignIn(organization.status);

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

  const toggleAccess = () =>
    void run(
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
              ? "Restoring sets the status to active, not back to what it was before."
              : "Blocks every member's sign-in. Nothing is deleted."}
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
        hint="Sets the new end date and lifts any suspension in one step."
      />
      <Button disabled={busy !== null || !endsAt} onClick={renew}>
        {busy === "renew" ? "Renewing…" : "Renew contract"}
      </Button>
    </ActionRail>
  );
}
