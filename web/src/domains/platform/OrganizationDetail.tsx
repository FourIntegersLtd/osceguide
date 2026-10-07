"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";
import {
  ActionRail,
  Alert,
  AsyncBoundary,
  B2CHero,
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
  contractDatesError,
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
  const requested = useSearchParams().get("tab");
  const [tab, setTab] = useState<Tab>(ORG_TABS.some((entry) => entry.id === requested) ? (requested as Tab) : "overview");
  const state = useAsync((signal) => readOrganization(slug, signal), [slug]);
  const [fresh, setFresh] = useState<Organization | null>(null);
  // Bumped when someone is seated, so the members list below reloads with them in it.
  const [seated, setSeated] = useState(0);

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
                description={`${ORG_TYPES.find((type) => type.value === current.org_type)?.label ?? current.org_type} · /${current.slug}`}
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
                <ContractHero organization={current} />
              ) : null}
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
                  <SeatMemberPanel slug={current.slug} orgType={current.org_type} onSeated={() => setSeated((n) => n + 1)} />
                  <MembersSection key={seated} slug={current.slug} orgType={current.org_type} />
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

const DAY_MS = 24 * 60 * 60 * 1000;

/** Shown only when the contract ends within thirty days, or already has. */
function ContractHero({ organization }: { organization: Organization }) {
  const [now] = useState(() => Date.now());
  if (!organization.contract_ends_at) return null;
  const days = Math.ceil(
    (new Date(organization.contract_ends_at).getTime() - now) / DAY_MS,
  );
  if (Number.isNaN(days) || days > 30) return null;
  return (
    <B2CHero
      eyebrow="Contract"
      title={
        days < 0
          ? "Contract has ended"
          : days === 0
            ? "Renewal due today"
            : `Renewal due in ${days} ${days === 1 ? "day" : "days"}`
      }
    >
      {`Contract ends ${formatDay(organization.contract_ends_at)}. Renew from the panel beside the details.`}
    </B2CHero>
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
            `Status "${organization.status}". Members can sign in but cannot open the organisation.`}
        </p>
        <FactList items={items} columns={3} />
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
  // Renewing sets the end date, so it may not fall before the stored start.
  const orderError = contractDatesError("", endsAt, {
    startsAt: organization.contract_starts_at?.slice(0, 10) ?? "",
    endsAt: "",
  });

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
              ? "Restoring makes the organisation active, even if it was on a trial before."
              : "Members can still sign in but cannot open the organisation. Nothing is deleted."}
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
        error={orderError}
        hint="Sets the new end date and lifts any suspension in one step."
      />
      <Button disabled={busy !== null || !endsAt || orderError !== null} onClick={renew}>
        {busy === "renew" ? "Renewing…" : "Renew contract"}
      </Button>
    </ActionRail>
  );
}
