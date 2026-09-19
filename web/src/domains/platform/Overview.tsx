"use client";

import Link from "next/link";
import { LuBuilding2, LuPencilRuler, LuTriangleAlert, LuUserCog, LuUsers } from "react-icons/lu";
import type { IconType } from "react-icons";
import { AsyncBoundary, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { listAllOrganizations, readOverview, type Organization } from "@/domains/platform/api";
import { Row, RowList, Section, StatusBadge } from "@/domains/platform/chrome";
import { permitsSignIn } from "@/domains/platform/support";

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
    <div className="flex flex-col gap-8">
      <PageHeader
        title={firstName ? `Hello, ${firstName}.` : "Platform"}
        description="Everything, across every organisation."
      />

      <AsyncBoundary state={state}>
        {({ overview, organizations }) => {
          const partners = organizations.filter((o) => o.org_type === "partner").length;
          const institutions = organizations.length - partners;
          const attention = organizations.filter((o) => !permitsSignIn(o.status));

          return (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Stat label="Organisations" value={overview.organizations} icon={LuBuilding2} />
                <Stat
                  label="Partners / institutions"
                  value={`${partners} / ${institutions}`}
                  icon={LuBuilding2}
                />
                <Stat label="Users" value={overview.users} icon={LuUsers} />
              </div>

              <Section title="Operations">
                <RowList>
                  <Destination
                    href={hrefFor("/organizations")}
                    title="Organisations"
                    subtitle="The directory, and provisioning a new tenant"
                    icon={LuBuilding2}
                  />
                  <Destination
                    href={hrefFor("/users")}
                    title="Users"
                    subtitle="Find an account, and who runs this console"
                    icon={LuUsers}
                  />
                  <Destination
                    href={hrefFor("/authoring")}
                    title="Authoring"
                    subtitle="The OSCE Guide catalogue every organisation draws on"
                    icon={LuPencilRuler}
                  />
                  <Destination
                    href={hrefFor("/settings")}
                    title="Your account"
                    subtitle="Your own profile and password"
                    icon={LuUserCog}
                  />
                </RowList>
              </Section>

              <Section
                title={`Needs attention (${attention.length})`}
                description="Organisations whose members cannot sign in today."
              >
                {attention.length === 0 ? (
                  <Card padding="md">
                    <p className="text-sm text-ink-muted">
                      Every organisation is active or on trial.
                    </p>
                  </Card>
                ) : (
                  <RowList>
                    {attention.map((organization) => (
                      <AttentionRow
                        key={organization.id}
                        organization={organization}
                        href={hrefFor(`/organizations/${encodeURIComponent(organization.slug)}`)}
                      />
                    ))}
                  </RowList>
                )}
              </Section>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}

function Stat({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: IconType;
}) {
  return (
    <Card padding="md">
      <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-ink-subtle">
        <Icon className="h-3.5 w-3.5" aria-hidden /> {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </Card>
  );
}

function Destination({
  href,
  title,
  subtitle,
  icon: Icon,
}: {
  href: string;
  title: string;
  subtitle: string;
  icon: IconType;
}) {
  return (
    <li>
      <Link
        href={href}
        className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-surface-raised"
      >
        <Icon className="h-4 w-4 shrink-0 text-ink-muted" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium text-ink">{title}</span>
          <span className="block truncate text-xs text-ink-subtle">{subtitle}</span>
        </span>
      </Link>
    </li>
  );
}

function AttentionRow({ organization, href }: { organization: Organization; href: string }) {
  return (
    <Row>
      <Link href={href} className="flex min-w-0 flex-1 items-center gap-3">
        <LuTriangleAlert className="h-4 w-4 shrink-0 text-ink-muted" aria-hidden />
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium text-ink">{organization.name}</span>
          <span className="block truncate text-xs text-ink-subtle">
            /{organization.slug} · {organization.org_type}
          </span>
        </span>
      </Link>
      <StatusBadge status={organization.status} />
    </Row>
  );
}

/** "Hello, Sam." — the first word of a name, or the local part of an address. */
function greetingName(name: string | undefined, email: string | undefined): string | undefined {
  const trimmed = name?.trim();
  if (trimmed) return trimmed.split(/\s+/)[0];
  return email?.split("@")[0]?.trim() || undefined;
}
