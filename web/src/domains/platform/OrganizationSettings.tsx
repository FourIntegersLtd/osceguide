"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Input, Panel, Select } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import {
  setStaffMfaPolicy,
  updateOrganization,
  type Organization,
  type OrganizationChanges,
} from "@/domains/platform/api";
import { WriteOnlyNote } from "@/domains/platform/chrome";
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

  const dirty =
    name.trim() !== organization.name || orgType !== organization.org_type;

  return (
    <div className="flex flex-col gap-6">
      <Panel title="Details">
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

          <Select
            label="Type"
            value={orgType}
            onChange={(event) => setOrgType(event.target.value)}
            disabled={busy}
            hint="Which console this tenant's members land in."
          >
            {ORG_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
            {/* A type the backend has and this app has not heard of must
                still be selectable, or saving anything else would change it. */}
            {ORG_TYPES.every((type) => type.value !== organization.org_type) ? (
              <option value={organization.org_type}>
                {organization.org_type}
              </option>
            ) : null}
          </Select>

          <div className="flex justify-end">
            <Button
              disabled={busy || !dirty || !name.trim()}
              onClick={() =>
                void commit(
                  { name: name.trim(), org_type: orgType },
                  "Details saved",
                )
              }
            >
              {busy ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </Panel>

      <ContractDates
        organization={organization}
        busy={busy}
        onCommit={commit}
      />
      <StaffMfaPolicy organization={organization} onChanged={onChanged} />
    </div>
  );
}

/**
 * Whether this tenant's staff must use two-factor sign-in.
 *
 * Takes effect at each person's next password sign-in, where anyone without
 * an authenticator is walked through setting one up. SSO sign-ins are the
 * identity provider's business and are not affected.
 */
function StaffMfaPolicy({
  organization,
  onChanged,
}: {
  organization: Organization;
  onChanged: (updated: Organization) => void;
}) {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const required = organization.require_staff_mfa;

  const toggle = async () => {
    setBusy(true);
    setError(null);
    try {
      onChanged(await setStaffMfaPolicy(organization.slug, !required));
      toast.success(
        required
          ? "Two-factor sign-in no longer required"
          : "Two-factor sign-in required",
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Panel title="Two-factor sign-in">
      <div className="flex max-w-lg flex-col gap-3">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
        <p className="text-osce-body text-ink">
          {required
            ? "Staff must sign in with a password and an authenticator code."
            : "Staff may sign in with a password alone. Each person can still turn two-factor sign-in on for themselves."}
        </p>
        <p className="text-osce-meta text-ink-subtle">
          Applies at each person&rsquo;s next password sign-in. Anyone without
          an authenticator sets one up then. Organisation (SSO) sign-in is
          unaffected.
        </p>
        <div className="flex justify-end">
          <Button
            variant={required ? "secondary" : "primary"}
            disabled={busy}
            onClick={() => void toggle()}
          >
            {busy
              ? "Saving…"
              : required
                ? "Stop requiring it"
                : "Require for staff"}
          </Button>
        </div>
      </div>
    </Panel>
  );
}

/**
 * The contract window. `contract_ends_at` is not decoration: a nightly sweep
 * suspends an organisation whose contract has lapsed.
 *
 * When the API omits dates from `OrganizationRead`, fields start empty and a
 * blank save leaves stored values untouched.
 */
function contractInputValue(iso: string | null | undefined): string {
  if (!iso) return "";
  const day = iso.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : "";
}

function ContractDates({
  organization,
  busy,
  onCommit,
}: {
  organization: Organization;
  busy: boolean;
  onCommit: (changes: OrganizationChanges, done: string) => Promise<void>;
}) {
  const [startsAt, setStartsAt] = useState(() =>
    contractInputValue(organization.contract_starts_at),
  );
  const [endsAt, setEndsAt] = useState(() =>
    contractInputValue(organization.contract_ends_at),
  );

  const save = () => {
    const changes: OrganizationChanges = {};
    if (startsAt) changes.contract_starts_at = asContractDate(startsAt);
    if (endsAt) changes.contract_ends_at = asContractDate(endsAt);
    if (Object.keys(changes).length === 0) return;
    void onCommit(changes, "Contract dates saved");
  };

  return (
    <Panel
      title="Contract"
      description="When this organisation's access starts, and when it lapses."
    >
      <div className="flex max-w-lg flex-col gap-3">
        {!organization.contract_starts_at && !organization.contract_ends_at ? (
          <WriteOnlyNote>
            Contract dates are not on this organisation record yet. A blank
            field is left untouched when you save.
          </WriteOnlyNote>
        ) : null}

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
    </Panel>
  );
}
