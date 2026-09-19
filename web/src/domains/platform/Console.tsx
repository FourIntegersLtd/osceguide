"use client";

import { useCallback, useState } from "react";
import { LuBuilding2, LuUsers } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, Card, Input, PageHeader } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import {
  createOrganization,
  listOrganizations,
  listUsers,
  readOverview,
  restoreOrganization,
  suspendOrganization,
} from "@/domains/platform/api";

/** The staff console: how many of everything, and the organisations. */
export function PlatformOverview() {
  const state = useAsync((signal) => readOverview(signal), []);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Platform" description="Everything, across every organisation." />
      <AsyncBoundary state={state}>
        {(data) => (
          <div className="grid gap-3 sm:grid-cols-2">
            <Card>
              <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-ink-subtle">
                <LuBuilding2 className="h-3.5 w-3.5" aria-hidden /> Organisations
              </p>
              <p className="mt-1 text-2xl font-semibold text-ink">{data.organizations}</p>
            </Card>
            <Card>
              <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-ink-subtle">
                <LuUsers className="h-3.5 w-3.5" aria-hidden /> Users
              </p>
              <p className="mt-1 text-2xl font-semibold text-ink">{data.users}</p>
            </Card>
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}

export function Organizations() {
  const state = useAsync((signal) => listOrganizations(signal), []);
  const [adding, setAdding] = useState(false);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Organisations"
        description="Institutions and employers. Both run sittings; the mode is what differs."
        actions={<Button onClick={() => setAdding((open) => !open)}>{adding ? "Cancel" : "Provision"}</Button>}
      />

      {adding && (
        <Provision
          onCreated={() => {
            setAdding(false);
            state.reload();
          }}
        />
      )}

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{ title: "No organisations yet" }}
      >
        {(page) => (
          <Card>
            <ul className="divide-y divide-border">
              {page.items.map((organization) => (
                <OrgRow key={organization.id} organization={organization} onChanged={state.reload} />
              ))}
            </ul>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}

function OrgRow({
  organization,
  onChanged,
}: {
  organization: { id: string; name: string; slug: string; org_type: string; status: string };
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const suspended = organization.status === "suspended";

  const toggle = useCallback(async () => {
    setBusy(true);
    try {
      await (suspended ? restoreOrganization(organization.slug) : suspendOrganization(organization.slug));
      onChanged();
    } finally {
      setBusy(false);
    }
  }, [suspended, organization.slug, onChanged]);

  return (
    <li className="flex flex-wrap items-center justify-between gap-3 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{organization.name}</p>
        <p className="truncate text-xs text-ink-subtle">
          /{organization.slug} · {organization.org_type}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone={suspended ? "danger" : "success"}>{organization.status}</Badge>
        <Button variant="secondary" size="sm" onClick={toggle} disabled={busy}>
          {suspended ? "Restore" : "Suspend"}
        </Button>
      </div>
    </li>
  );
}

function Provision({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [orgType, setOrgType] = useState("institution");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await createOrganization({ name: name.trim(), slug: slug.trim(), orgType });
        onCreated();
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [name, slug, orgType, onCreated],
  );

  return (
    <Card title="Provision an organisation">
      <form onSubmit={submit} className="flex max-w-lg flex-col gap-3">
        {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
        <Input
          label="Name"
          required
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            // Slug follows the name until somebody edits it themselves.
            setSlug((current) =>
              current === slugify(name) || current === "" ? slugify(event.target.value) : current,
            );
          }}
        />
        <Input
          label="Slug"
          required
          value={slug}
          onChange={(event) => setSlug(event.target.value)}
          hint="Appears in every URL for this workspace, and cannot be changed casually."
        />
        <label className="flex flex-col gap-1.5">
          <span className="text-sm font-medium text-ink">Type</span>
          <select
            value={orgType}
            onChange={(event) => setOrgType(event.target.value)}
            className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
          >
            <option value="institution">Institution</option>
            <option value="partner">Partner</option>
            <option value="employer">Employer</option>
          </select>
        </label>
        <div className="flex justify-end">
          <Button type="submit" disabled={busy || !name.trim() || !slug.trim()}>
            Provision
          </Button>
        </div>
      </form>
    </Card>
  );
}

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function Users() {
  const state = useAsync((signal) => listUsers(signal), []);
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Users" description="Everyone with an account." />
      <AsyncBoundary state={state} isEmpty={(page) => page.items.length === 0} empty={{ title: "No users" }}>
        {(page) => (
          <Card>
            <ul className="divide-y divide-border">
              {page.items.map((user) => (
                <li key={user.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink">{user.name}</p>
                    <p className="truncate text-xs text-ink-subtle">{user.email}</p>
                  </div>
                  <span className="text-xs text-ink-subtle">
                    joined {new Date(user.created_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </AsyncBoundary>
    </div>
  );
}
