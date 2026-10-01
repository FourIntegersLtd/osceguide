"use client";

import { useEffect, useMemo, useState } from "react";
import { LuBuilding2 } from "react-icons/lu";
import {
  AsyncBoundary,
  Button,
  EmptyPanel,
  Panel,
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
  PlatformPageHeader,
  RowLink,
  RowList,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  listAllOrganizations,
  type Organization,
} from "@/domains/platform/api";
import { StatusBadge } from "@/domains/platform/chrome";
import { ProvisionModal } from "@/domains/platform/ProvisionPanel";
import { ORG_STATUSES, ORG_TYPES } from "@/domains/platform/support";

type TypeFilter = "all" | string;

/**
 * The tenant directory: partners and institutions, grouped by type.
 *
 * Status, type and search all go to the backend (`GET /platform/organizations`
 * takes `status`, `org_type` and `search`), so the directory is no longer
 * walked whole to be searched in the browser.
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
  // What the server is asked: the box, once typing pauses.
  const [query, setQuery] = useState("");
  const [provisioning, setProvisioning] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(search.trim()), 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  const state = useAsync(
    (signal) =>
      listAllOrganizations(
        {
          status: status || null,
          search: query || null,
          orgType: typeFilter === "all" ? null : typeFilter,
        },
        signal,
      ),
    [status, query, typeFilter],
  );

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Organisations"
        description="Institutions and partners. Both run exams; they differ in how their exams are run."
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
        <PlatformFilterSelect
          aria-label="Status"
          value={status}
          onChange={setStatus}
        >
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
          query || typeFilter !== "all"
            ? {
                title: "Nothing matches those filters",
                description: "Try a different name, or clear the type filter.",
              }
            : status
              ? {
                  title: `No organisation is ${status}`,
                  description:
                    "Clear the status filter to see the rest of the directory.",
                  action: (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setStatus("")}
                    >
                      Clear the filter
                    </Button>
                  ),
                }
              : {
                  title: "No organisations yet",
                  description:
                    "Create one to give a customer their own space.",
                }
        }
      >
        {(rows) => (
          <Directory rows={rows} typeFilter={typeFilter} hrefFor={hrefFor} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Directory({
  rows,
  typeFilter,
  hrefFor,
}: {
  rows: Organization[];
  typeFilter: TypeFilter;
  hrefFor: (path: string) => string;
}) {
  const groups = useMemo(() => {
    // Already filtered by the backend; this only groups by type.
    const visible = rows;
    return ORG_TYPES.map((type) => ({
      ...type,
      rows: visible.filter((row) => row.org_type === type.value),
      // An org_type the frontend has not heard of still has to appear
      // somewhere, and the first group is where the odd one out goes.
      extra:
        type.value === ORG_TYPES[0].value
          ? visible.filter(
              (row) => !ORG_TYPES.some((t) => t.value === row.org_type),
            )
          : [],
    })).filter((group) => typeFilter === "all" || group.value === typeFilter);
  }, [rows, typeFilter]);

  const total = groups.reduce(
    (sum, group) => sum + group.rows.length + group.extra.length,
    0,
  );

  if (total === 0) {
    return (
      <EmptyPanel
        title="Nothing matches those filters"
        description="Try a different name, or clear the type filter."
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {groups.map((group) => {
        const groupRows = [...group.rows, ...group.extra];
        if (groupRows.length === 0) return null;
        return (
          <Panel
            key={group.value}
            title={`${group.label}s · ${groupRows.length}`}
            padding="none"
          >
            <RowList flush>
              {groupRows.map((organization) => (
                <RowLink
                  key={organization.id}
                  href={hrefFor(
                    `/organizations/${encodeURIComponent(organization.slug)}`,
                  )}
                  title={organization.name}
                  subtitle={`/${organization.slug} · ${organization.org_type}`}
                  trailing={<StatusBadge status={organization.status} />}
                />
              ))}
            </RowList>
          </Panel>
        );
      })}
    </div>
  );
}
