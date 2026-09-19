"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Card, Input } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import {
  updateOrganization,
  type Organization,
  type OrganizationChanges,
} from "@/domains/platform/api";
import { Section, WriteOnlyNote } from "@/domains/platform/chrome";
import { ORG_TYPES, asContractDate } from "@/domains/platform/support";

/**
 * What a platform administrator may change about an organisation.
 *
 * Not the slug: every foreign key points at the row's id and the slug is the
 * URL, so renaming one is a redirect problem rather than a field edit. The
 * backend refuses it for that reason, and the field is read-only here rather
 * than absent, because "why can I not rename this?" is a question worth
 * answering on the screen.
 */
export function OrganizationSettings({
  organization,
  onChanged,
}: {
  organization: Organization;
  onChanged: (updated: Organization) => void;
}) {
  const toast = useToast();
  const [name, setName] = useState(organization.name);
  const [orgType, setOrgType] = useState(organization.org_type);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const commit = useCallback(
    async (changes: OrganizationChanges, done: string) => {
      setBusy(true);
      setError(null);
      try {
        onChanged(await updateOrganization(organization.slug, changes));
        toast.success(done);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [organization.slug, onChanged, toast],
  );

  const dirty = name.trim() !== organization.name || orgType !== organization.org_type;

  return (
    <div className="flex flex-col gap-8">
      <Section title="Details">
        <Card padding="md">
          <div className="flex max-w-lg flex-col gap-3">
            {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}

            <Input
              label="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              disabled={busy}
            />

            <Input
              label="Slug"
              value={organization.slug}
              readOnly
              hint="The URL every one of this tenant's screens hangs off. It cannot be changed."
            />

            <label className="flex flex-col gap-1.5">
              <span className="text-osce-meta font-medium text-osce-ink-700">Type</span>
              <select
                value={orgType}
                onChange={(event) => setOrgType(event.target.value)}
                disabled={busy}
                className="h-10 rounded-control border border-border-strong bg-surface px-3 text-sm text-ink"
              >
                {ORG_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
                {/* A type the backend has and this app has not heard of must
                    still be selectable, or saving anything else would change it. */}
                {ORG_TYPES.every((type) => type.value !== organization.org_type) ? (
                  <option value={organization.org_type}>{organization.org_type}</option>
                ) : null}
              </select>
              <span className="text-osce-meta text-b2c-text-muted">
                Which console this tenant&rsquo;s members land in.
              </span>
            </label>

            <div className="flex justify-end">
              <Button
                disabled={busy || !dirty || !name.trim()}
                onClick={() =>
                  void commit({ name: name.trim(), org_type: orgType }, "Details saved")
                }
              >
                {busy ? "Saving…" : "Save"}
              </Button>
            </div>
          </div>
        </Card>
      </Section>

      <ContractDates busy={busy} onCommit={commit} />
    </div>
  );
}

/**
 * The contract window, which the backend takes and does not give back.
 *
 * `contract_ends_at` is not decoration: a nightly sweep suspends an
 * organisation whose contract has lapsed, which is what puts it on the
 * overview's "needs attention" list. `OrganizationRead` carries neither date,
 * so these fields start empty on every visit and cannot show what is stored —
 * recorded in `docs/port-gaps.md`.
 *
 * That is also why an empty field is never sent. Submitting a blank form would
 * silently clear dates this screen cannot see; clearing one is its own button,
 * and it says what it will do.
 */
function ContractDates({
  busy,
  onCommit,
}: {
  busy: boolean;
  onCommit: (changes: OrganizationChanges, done: string) => Promise<void>;
}) {
  const [startsAt, setStartsAt] = useState("");
  const [endsAt, setEndsAt] = useState("");

  const save = () => {
    const changes: OrganizationChanges = {};
    if (startsAt) changes.contract_starts_at = asContractDate(startsAt);
    if (endsAt) changes.contract_ends_at = asContractDate(endsAt);
    if (Object.keys(changes).length === 0) return;
    void onCommit(changes, "Contract dates saved");
  };

  return (
    <Section
      title="Contract"
      description="When this organisation's access starts, and when it lapses."
    >
      <Card padding="md">
        <div className="flex max-w-lg flex-col gap-3">
          <WriteOnlyNote>
            The API accepts these dates and does not return them, so this form cannot show what is
            stored. A blank field is left untouched when you save.
          </WriteOnlyNote>

          <Input
            type="date"
            label="Access starts"
            value={startsAt}
            onChange={(event) => setStartsAt(event.target.value)}
            disabled={busy}
          />

          <Input
            type="date"
            label="Access ends"
            value={endsAt}
            onChange={(event) => setEndsAt(event.target.value)}
            disabled={busy}
            hint="Midnight at the start of this day. A lapsed contract suspends the organisation."
          />

          <div className="flex flex-wrap justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={busy}
              onClick={() =>
                void onCommit(
                  { contract_starts_at: null, contract_ends_at: null },
                  "Contract dates cleared",
                )
              }
            >
              Clear both dates
            </Button>
            <Button disabled={busy || (!startsAt && !endsAt)} onClick={save}>
              {busy ? "Saving…" : "Save dates"}
            </Button>
          </div>
        </div>
      </Card>
    </Section>
  );
}
