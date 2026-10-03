"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, Button, Input, Modal, Select } from "@/foundation/ui";
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
 * them a link.
 */
export function ProvisionForm({
  onProvisioned,
  onCancel,
}: {
  onProvisioned: (organization: Organization) => void;
  onCancel?: () => void;
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
        toast.success(`Created ${organization.slug}`, "Next, add its first administrator.");
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
    <form onSubmit={submit} className="flex flex-col gap-5">
      {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

      <Input
        label="Organisation name"
        required
        value={name}
        onChange={(event) => {
          const next = event.target.value;
          setName(next);
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
        hint="Used in every web address for this organisation. It cannot be changed afterwards."
      />

      <Select
        label="Type"
          value={orgType}
          onChange={(event) => setOrgType(event.target.value)}
          hint="For an employer, choose Institution: employers run exams the same way."
        >
          {ORG_TYPES.map((type) => (
            <option key={type.value} value={type.value}>
              {type.label}
            </option>
          ))}
        </Select>

      <div className="flex justify-end gap-2 pt-1">
        {onCancel ? (
          <Button type="button" variant="ghost" disabled={busy} onClick={onCancel}>
            Cancel
          </Button>
        ) : null}
        <Button type="submit" variant="commit" disabled={busy || !name.trim() || !slug.trim()}>
          {busy ? "Creating…" : "Create organisation"}
        </Button>
      </div>
    </form>
  );
}

export function ProvisionModal({
  open,
  onClose,
  onProvisioned,
}: {
  open: boolean;
  onClose: () => void;
  onProvisioned: (organization: Organization) => void;
}) {
  const [formKey, setFormKey] = useState(0);

  useEffect(() => {
    if (open) setFormKey((key) => key + 1);
  }, [open]);

  if (!open) return null;

  return (
    <Modal
      onClose={onClose}
      title="Set up an organisation"
      width="min(32rem, 96vw)"
    >
      <div className="p-4 lg:p-6">
        <ProvisionForm
          key={formKey}
          onCancel={onClose}
          onProvisioned={(organization) => {
            onProvisioned(organization);
            onClose();
          }}
        />
      </div>
    </Modal>
  );
}
