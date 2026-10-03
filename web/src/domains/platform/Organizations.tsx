"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import Table, { type TableMore } from "@/foundation/table/Table";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import {
  AsyncBoundary,
  Button,
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSearch,
  PlatformFilterSelect,
  PlatformPageHeader,
} from "@/foundation/ui";
import { useCursorPages, useSearchQuery } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import {
  listOrganizations,
  type Organization,
} from "@/domains/platform/api";
import { StatusBadge } from "@/domains/platform/chrome";
import { ProvisionModal } from "@/domains/platform/ProvisionPanel";
import { ORG_STATUSES, ORG_TYPES, formatDay } from "@/domains/platform/support";

type TypeFilter = "all" | string;

/**
 * The tenant directory: partners and institutions, grouped by type.
 *
 * Status, type and search all go to the backend (`GET /platform/organizations`
 * takes `status`, `org_type` and `search`), and the directory is read one
 * server page at a time, so it is never walked whole to draw or search it.
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
  const query = useSearchQuery(search);
  const [provisioning, setProvisioning] = useState(false);

  const pages = useCursorPages<Organization>(
    (cursor, signal) =>
      listOrganizations(
        {
          status: status || null,
          search: query || null,
          orgType: typeFilter === "all" ? null : typeFilter,
          cursor,
        },
        signal,
      ),
    [status, query, typeFilter],
  );

  return (
    <div className="flex flex-col gap-6">
      <PlatformPageHeader
        title="Organisations"
        description="Institutions and partners."
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
          pages.state.reload();
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
          placeholder="Search organisations"
          aria-label="Search organisations"
        />
      </PlatformFilterBar>

      <AsyncBoundary
        state={pages.state}
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
          <Directory rows={rows} more={pages} hrefFor={hrefFor} />
        )}
      </AsyncBoundary>
    </div>
  );
}

function Directory({
  rows,
  more,
  hrefFor,
}: {
  rows: Organization[];
  more: TableMore;
  hrefFor: (path: string) => string;
}) {
  const columns = useMemo(
    () => [
      {
        header: "Organisation",
        key: "name" as keyof Organization,
        priority: "primary" as const,
        render: (organization: Organization) => (
          <Link
            href={hrefFor(
              `/organizations/${encodeURIComponent(organization.slug)}`,
            )}
            className={cn(b2cTableCellText, "font-medium text-ink hover:text-accent")}
          >
            {organization.name}
          </Link>
        ),
      },
      {
        header: "Type",
        key: "org_type" as keyof Organization,
        render: (organization: Organization) => (
          <span className={b2cTableCellText}>
            {ORG_TYPES.find((type) => type.value === organization.org_type)
              ?.label ?? organization.org_type}
          </span>
        ),
      },
      {
        header: "Status",
        key: "status" as keyof Organization,
        render: (organization: Organization) => (
          <StatusBadge status={organization.status} />
        ),
      },
      {
        header: "Contract ends",
        key: "contract_ends_at" as keyof Organization,
        render: (organization: Organization) => (
          <span className={b2cTableCellText}>
            {formatDay(organization.contract_ends_at)}
          </span>
        ),
      },
    ],
    [hrefFor],
  );
  return (
    <Table<Organization>
      columns={columns}
      idField="id"
      rows={rows}
      more={more}
    />
  );
}
