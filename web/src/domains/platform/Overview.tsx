"use client";

import Link from "next/link";
import {
  LuBuilding2,
  LuScrollText,
  LuTriangleAlert,
  LuUsers,
} from "react-icons/lu";
import {
  AsyncBoundary,
  B2CHero,
  ButtonLink,
  EmptyPanel,
  Panel,
  PlatformPageHeader,
  RowLink,
  RowList,
  StatGrid,
  StatTile,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOverview } from "@/domains/platform/api";
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
    }),
    [],
  );

  const firstName = greetingName(session?.user.name, session?.user.email);

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title={firstName ? `Hello, ${firstName}.` : "Platform"}
        description="Everything across every organisation, in one place."
      />

      <AsyncBoundary state={state}>
        {({ overview }) => {
          const attention = overview.at_risk ?? [];
          const first = attention[0];

          return (
            <>
              <B2CHero
                title={
                  attention.length === 0
                    ? "Nothing is waiting on the team"
                    : `${attention.length} ${attention.length === 1 ? "organisation is" : "organisations are"} waiting on the team`
                }
                action={
                  first ? (
                    <ButtonLink
                      href={hrefFor(
                        `/organizations/${encodeURIComponent(first.slug)}`,
                      )}
                      variant="secondary"
                    >
                      Open the first
                    </ButtonLink>
                  ) : null
                }
              >
                {attention.length === 0
                  ? "Every organisation is active or on trial."
                  : "Suspended, lapsed, or ending within thirty days."}
              </B2CHero>

              <StatGrid>
                <StatTile
                  label="Organisations"
                  value={overview.organizations}
                  icon={LuBuilding2}
                />
                <StatTile label="Users" value={overview.users} icon={LuUsers} />
              </StatGrid>

              <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
                <Panel title="Needs attention" padding="none">
                  {attention.length === 0 ? (
                    <EmptyPanel
                      bare
                      title="All clear"
                      description="Every organisation is active or on trial."
                    />
                  ) : (
                    <RowList flush>
                      {attention.map((risk) => (
                        <AttentionRow
                          key={risk.slug}
                          organization={risk}
                          href={hrefFor(
                            `/organizations/${encodeURIComponent(risk.slug)}`,
                          )}
                        />
                      ))}
                    </RowList>
                  )}
                </Panel>

                <Panel title="Go to" padding="none">
                  <RowList flush>
                    <RowLink
                      href={hrefFor("/organizations")}
                      title="Provision an organisation"
                      subtitle="Opens the organisations list, where Provision is"
                      icon={LuBuilding2}
                    />
                    <RowLink
                      href={hrefFor("/users")}
                      title="Find a user"
                      subtitle="Search accounts by name or email"
                      icon={LuUsers}
                    />
                    <RowLink
                      href={hrefFor("/audit")}
                      title="Audit log"
                      subtitle="Who changed what, across the platform"
                      icon={LuScrollText}
                    />
                  </RowList>
                </Panel>
              </div>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function AttentionRow({
  organization,
  href,
}: {
  organization: OrgAtRisk;
  href: string;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3 px-5 py-3.5 transition-colors hover:bg-surface-raised sm:px-6"
      >
        <LuTriangleAlert
          className="h-4 w-4 shrink-0 text-osce-warning-icon"
          aria-hidden
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-osce-data font-medium text-ink">
            {organization.name}
          </span>
          <span className="block truncate text-osce-meta text-ink-subtle">
            /{organization.slug} · {atRiskLabel(organization.reason)}
          </span>
        </span>
        <StatusBadge status={organization.status} />
      </Link>
    </li>
  );
}

/** "Hello, Sam." — the first word of a name, or the local part of an address. */
function greetingName(
  name: string | undefined,
  email: string | undefined,
): string | undefined {
  const trimmed = name?.trim();
  if (trimmed) return trimmed.split(/\s+/)[0];
  return email?.split("@")[0]?.trim() || undefined;
}
