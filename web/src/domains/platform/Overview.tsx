"use client";

import Link from "next/link";
import { useState } from "react";
import { LuBuilding2, LuScrollText, LuUsers } from "react-icons/lu";
import {
  AsyncBoundary,
  B2CGroupedRowLink,
  B2CGroupedSection,
  B2CHero,
  B2CPageHeader,
  ButtonLink,
  StatGrid,
  StatTile,
} from "@/foundation/ui";
import Table from "@/foundation/table/Table";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { readOverview } from "@/domains/platform/api";
import type { OrgAtRisk } from "@/domains/platform/support/api";
import { StatusBadge } from "@/domains/platform/chrome";
import { atRiskLabel, pageOf } from "@/domains/platform/support";

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
      <B2CPageHeader
        title={firstName ? `Hello, ${firstName}.` : "Platform"}
        subtitle="Everything across every organisation, in one place."
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
                  ? "None is suspended, lapsed or ending within thirty days."
                  : "Suspended, lapsed, or ending within thirty days."}
              </B2CHero>

              <StatGrid>
                <StatTile label="Organisations" value={overview.organizations} />
                <StatTile label="Users" value={overview.users} />
              </StatGrid>

              <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-2">
                <AttentionList attention={attention} hrefFor={hrefFor} />

                <B2CGroupedSection eyebrow="Go to">
                  <B2CGroupedRowLink
                    href={hrefFor("/organizations")}
                    title="Provision an organisation"
                    meta="Opens the organisations list, where Provision is"
                    icon={LuBuilding2}
                  />
                  <B2CGroupedRowLink
                    href={hrefFor("/users")}
                    title="Find a user"
                    meta="Search accounts by name or email"
                    icon={LuUsers}
                  />
                  <B2CGroupedRowLink
                    href={hrefFor("/audit")}
                    title="Audit log"
                    meta="Who changed what, across the platform"
                    icon={LuScrollText}
                  />
                </B2CGroupedSection>
              </div>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

/** Ten at a time: a platform with many lapsing contracts should not push everything else off the screen. */
function AttentionList({
  attention,
  hrefFor,
}: {
  attention: OrgAtRisk[];
  hrefFor: (path: string) => string;
}) {
  const [pages, setPages] = useState(1);
  const shown = pageOf(attention, pages);
  return (
    <Table<OrgAtRisk>
      rows={shown}
      themeType="b2b"
      idField="slug"
      title="Needs attention"
      empty={{
        title: "All clear",
        description: "None is suspended, lapsed or ending within thirty days.",
      }}
      more={{
        hasMore: shown.length < attention.length,
        loadingMore: false,
        moreError: null,
        loadMore: () => setPages(pages + 1),
      }}
      columns={[
        {
          header: "Organisation",
          key: "name",
          priority: "primary",
          render: (risk) => (
            <div className="min-w-0">
              <Link
                href={hrefFor(`/organizations/${encodeURIComponent(risk.slug)}`)}
                className="font-medium text-ink hover:underline"
              >
                {risk.name}
              </Link>
              <p className="truncate text-osce-meta text-ink-subtle">
                /{risk.slug} · {atRiskLabel(risk.reason)}
              </p>
            </div>
          ),
        },
        {
          header: "Status",
          key: "status",
          render: (risk) => <StatusBadge status={risk.status} />,
        },
      ]}
    />
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
