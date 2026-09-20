"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { LuChevronRight } from "react-icons/lu";
import { AsyncBoundary, Button, Card } from "@/foundation/ui";
import { LuBuilding2 } from "react-icons/lu";
import { PlatformPageHeader } from "@/domains/platform/PlatformPageHeader";
import {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
} from "@/domains/platform/PlatformFilterBar";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listAllOrganizations, type Organization } from "@/domains/platform/api";
import { Row, RowList, Section, StatusBadge } from "@/domains/platform/chrome";
import { ProvisionModal } from "@/domains/platform/ProvisionPanel";
import { ORG_STATUSES, ORG_TYPES, matchesSearch } from "@/domains/platform/support";

type TypeFilter = "all" | string;

/**
 * The tenant directory: partners and institutions, grouped by type.
 *
 * The status filter is the backend's — `GET /platform/organizations` takes
 * one — and changing it reloads. The search box and the type filter are over
 * what has been paged in, because the endpoint takes neither; the whole
 * directory is walked for exactly that reason, and `docs/port-gaps.md` says
 * where that stops scaling.
 *
 * There is no delete. The backend will not delete an organisation and that is
 * a decision, not an omission: a tenant's rows include candidate results that
 * exist to be defensible months later. Suspension is the reversible mechanism,
 * and it is on the organisation's own screen.
 */
export function Organizations() {
  const { hrefFor } = useSurface();
  const [status, setStatus] = useState<string>("");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [search, setSearch] = useState("");
  const [provisioning, setProvisioning] = useState(false);

  const state = useAsync(
    (signal) => listAllOrganizations(status || null, signal),
    [status],
  );

  return (
    <div className="flex flex-col gap-8">
      <PlatformPageHeader
        title="Organisations"
        description="Institutions and partners. Both run sittings; the mode is what differs."
        icon={LuBuilding2}
        actions={
          <Button variant="primary" onClick={() => setProvisioning(true)}>
            Provision
          </Button>
        }
      />

      <ProvisionModal
        open={provisioning}
        onClose={() => setProvisioning(false)}
        onProvisioned={() => {
          state.reload();
        }}
      />

      <PlatformFilterBar>
        <PlatformFilterSelect
          aria-label="Type"
          value={typeFilter}
          onChange={(value) => setTypeFilter(value as TypeFilter)}
        >
          <option value="all">All types</option>
          {ORG_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSelect aria-label="Status" value={status} onChange={setStatus}>
          <option value="">All statuses</option>
          {ORG_STATUSES.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </PlatformFilterSelect>
        <PlatformFilterDivider />
        <PlatformFilterSearch
          value={search}
          onChange={setSearch}
          placeholder="Search name or slug"
          aria-label="Search organisations"
        />
      </PlatformFilterBar>

      <AsyncBoundary
        state={state}
        isEmpty={(rows) => rows.length === 0}
        /*
         * The empty state has to say which emptiness this is. The status
         * filter is the backend's, so filtering to one nothing is in emptied
         * the whole listing and the screen said "No organisations yet" on a
         * platform with six of them — the same class of lie as a failed load
         * rendering as no data.
         */
        empty={
          status
            ? {
                title: `No organisation is ${status}`,
                description: "Clear the status filter to see the rest of the directory.",
                action: (
                  <Button variant="secondary" size="sm" onClick={() => setStatus("")}>
                    Clear the filter
                  </Button>
                ),
              }
            : {
                title: "No organisations yet",
                description: "Provision one to give a customer its workspace.",
              }
        }
      >
        {(rows) => <Directory rows={rows} typeFilter={typeFilter} search={search} hrefFor={hrefFor} />}
      </AsyncBoundary>
    </div>
  );
}

function Directory({
  rows,
  typeFilter,
  search,
  hrefFor,
}: {
  rows: Organization[];
  typeFilter: TypeFilter;
  search: string;
  hrefFor: (path: string) => string;
}) {
  const groups = useMemo(() => {
    const visible = rows.filter(
      (row) =>
        (typeFilter === "all" || row.org_type === typeFilter) && matchesSearch(row, search),
    );
    return ORG_TYPES.map((type) => ({
      ...type,
      rows: visible.filter((row) => row.org_type === type.value),
      // An org_type the frontend has not heard of still has to appear
      // somewhere, and the first group is where the odd one out goes.
      extra: type.value === ORG_TYPES[0].value
        ? visible.filter((row) => !ORG_TYPES.some((t) => t.value === row.org_type))
        : [],
    })).filter((group) => typeFilter === "all" || group.value === typeFilter);
  }, [rows, typeFilter, search]);

  const total = groups.reduce((sum, group) => sum + group.rows.length + group.extra.length, 0);

  if (total === 0) {
    return (
      <Card padding="md">
        <p className="text-sm text-ink-muted">Nothing matches those filters.</p>
      </Card>
    );
  }

  return (
    <>
      {groups.map((group) => {
        const groupRows = [...group.rows, ...group.extra];
        if (groupRows.length === 0) return null;
        return (
          <Section key={group.value} title={`${group.label}s · ${groupRows.length}`}>
            <RowList>
              {groupRows.map((organization) => (
                <Row key={organization.id} className="px-0 py-0">
                  <Link
                    href={hrefFor(`/organizations/${encodeURIComponent(organization.slug)}`)}
                    className="flex min-w-0 flex-1 items-center gap-3 px-5 py-3 transition-colors hover:bg-surface-raised"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm font-medium text-ink">
                        {organization.name}
                      </span>
                      <span className="block truncate text-xs text-ink-subtle">
                        /{organization.slug} · {organization.org_type}
                      </span>
                    </span>
                    <StatusBadge status={organization.status} />
                    <LuChevronRight className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
                  </Link>
                </Row>
              ))}
            </RowList>
          </Section>
        );
      })}
    </>
  );
}
