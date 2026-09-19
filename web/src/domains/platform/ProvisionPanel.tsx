"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { provisionOrganization, type Organization } from "@/domains/platform/api";
import { ORG_TYPES, slugify } from "@/domains/platform/support";

/**
 * Provisioning a tenant: a name, a slug and which console its members land in.
 *
 * Three fields where the retiring form had five. The other two were an admin
 * email and a temporary password generated in the browser, displayed for an
 * administrator to relay by hand — `platform-api` has no bootstrap-admin
 * route, and no password passes through this app at all. The first member is
 * seated on the organisation's own screen, by address, and the backend emails
 * them a link. See `docs/port-gaps.md`.
 */
export function ProvisionPanel({
  onProvisioned,
}: {
  onProvisioned: (organization: Organization) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [orgType, setOrgType] = useState<string>(ORG_TYPES[0].value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        const organization = await provisionOrganization({
          name: name.trim(),
          slug: slug.trim(),
          orgType,
        });
        toast.success(`Provisioned ${organization.slug}`, "Seat its first administrator next.");
        setName("");
        setSlug("");
        setSlugEdited(false);
        onProvisioned(organization);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [name, slug, orgType, onProvisioned, toast],
  );

  return (
    <Card title="Provision an organisation">
      <form onSubmit={submit} className="flex max-w-lg flex-col gap-3 p-5">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

        <Input
          label="Name"
          required
          value={name}
          onChange={(event) => {
            const next = event.target.value;
            setName(next);
            // The slug follows the name until somebody edits it themselves.
            if (!slugEdited) setSlug(slugify(next));
          }}
        />

        <Input
          label="Slug"
          required
          value={slug}
          onChange={(event) => {
            setSlugEdited(true);
            setSlug(event.target.value);
          }}
          hint="Appears in every URL for this workspace. It cannot be changed afterwards."
        />

        <label className="flex flex-col gap-1.5">
          <span className="text-osce-meta font-medium text-osce-ink-700">Type</span>
          <select
            value={orgType}
            onChange={(event) => setOrgType(event.target.value)}
            className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
          >
            {ORG_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <span className="text-osce-meta text-b2c-text-muted">
            An employer is an institution running exam-mode sittings, not a third kind.
          </span>
        </label>

        <div className="flex justify-end">
          <Button type="submit" disabled={busy || !name.trim() || !slug.trim()}>
            {busy ? "Provisioning…" : "Provision"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
