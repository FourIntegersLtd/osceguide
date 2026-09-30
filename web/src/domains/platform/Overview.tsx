"use client";

import Link from "next/link";
import { LuBuilding2, LuGauge, LuPencilRuler, LuTriangleAlert, LuUserCog, LuUsers } from "react-icons/lu";
import { AsyncBoundary, Panel, PlatformPageHeader, RowLink, StatGrid, StatTile } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listAllOrganizations, readOverview } from "@/domains/platform/api";
import type { OrgAtRisk } from "@/domains/platform/support/api";
import { StatusBadge } from "@/domains/platform/chrome";
import { atRiskLabel } from "@/domains/platform/support";

/**
 * The console's first screen: how many of everything, and what needs a look.
 *
 * The retiring dashboard opened on tenant health — four counts and a list of
 * at-risk tenants. Two of those counts were activity over thirty days, which
 * `GET /platform/overview` does not answer; what it does answer is the two
 * totals, and the directory supplies the rest.
 *
 * "Needs attention" is therefore the organisations whose members cannot sign
 * in, rather than the old contract-derived risk list: `OrganizationRead`
 * carries no contract dates. Same purpose, narrower evidence — and the sweep
 * that suspends a lapsed contract puts its tenants in exactly this list.
 *
 * The two panels sit side by side from `lg`: attention is the thing to act
 * on, and "Go to" is the thing to act with, so they read as one decision
 * rather than a stack of unrelated lists.
 */
export function PlatformOverview() {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => ({
      overview: await readOverview(signal),
      organizations: await listAllOrganizations(null, signal),
    }),
    [],
  );

  const firstName = greetingName(session?.user.name, session?.user.email);

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title={firstName ? `Hello, ${firstName}.` : "Platform"}
        description="Everything, across every organisation."
        icon={LuGauge}
      />

      <AsyncBoundary state={state}>
        {({ overview, organizations }) => {
          const partners = organizations.filter((o) => o.org_type === "partner").length;
          const institutions = organizations.length - partners;
          const attention = overview.at_risk ?? [];

          return (
            <>
              <StatGrid>
                <StatTile label="Organisations" value={overview.organizations} icon={LuBuilding2} />
                <StatTile
                  label="Partners / institutions"
                  value={`${partners} / ${institutions}`}
                  icon={LuBuilding2}
                />
                <StatTile label="Users" value={overview.users} icon={LuUsers} />
              </StatGrid>

              <div className="grid items-start gap-6 lg:grid-cols-2">
                <Panel
                  title={`Needs attention (${attention.length})`}
                  description="Suspended, lapsed, or ending within thirty days."
                  padding="none"
                >
                  {attention.length === 0 ? (
                    <p className="px-5 py-4 text-osce-data text-b2c-text-muted sm:px-6">
                      Every organisation is active or on trial.
                    </p>
                  ) : (
                    <ul className="divide-y divide-b2c-border">
                      {attention.map((risk) => (
                        <AttentionRow
                          key={risk.slug}
                          organization={risk}
                          href={hrefFor(`/organizations/${encodeURIComponent(risk.slug)}`)}
                        />
                      ))}
                    </ul>
                  )}
                </Panel>

                <Panel title="Go to" padding="none">
                  <ul className="divide-y divide-b2c-border">
                    <RowLink
                      href={hrefFor("/organizations")}
                      title="Organisations"
                      subtitle="The directory, and provisioning a new tenant"
                      icon={LuBuilding2}
                    />
                    <RowLink
                      href={hrefFor("/users")}
                      title="Users"
                      subtitle="Find an account, and who runs this console"
                      icon={LuUsers}
                    />
                    <RowLink
                      href={`${hrefFor("/authoring")}/stations`}
                      title="Authoring"
                      subtitle="The OSCE Guide catalogue every organisation draws on"
                      icon={LuPencilRuler}
                    />
                    <RowLink
                      href={hrefFor("/settings")}
                      title="Your account"
                      subtitle="Your own profile and password"
                      icon={LuUserCog}
                    />
                  </ul>
                </Panel>
              </div>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function AttentionRow({ organization, href }: { organization: OrgAtRisk; href: string }) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-b2c-surface-muted sm:px-6"
      >
        <LuTriangleAlert className="h-4 w-4 shrink-0 text-osce-warning-icon" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-osce-data font-medium text-osce-ink-900">
            {organization.name}
          </span>
          <span className="block truncate text-osce-meta text-b2c-text-muted">
            /{organization.slug} · {atRiskLabel(organization.reason)}
          </span>
        </span>
        <StatusBadge status={organization.status} />
      </Link>
    </li>
  );
}

/** "Hello, Sam." — the first word of a name, or the local part of an address. */
function greetingName(name: string | undefined, email: string | undefined): string | undefined {
  const trimmed = name?.trim();
  if (trimmed) return trimmed.split(/\s+/)[0];
  return email?.split("@")[0]?.trim() || undefined;
}
