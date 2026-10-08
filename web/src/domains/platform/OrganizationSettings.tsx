"use client";

import { useCallback, useState } from "react";
import { Alert, Button, Input, Panel, Select } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import {
  listAllOrgMemberships,
  setStaffMfaPolicy,
  updateOrganization,
  type Organization,
  type Membership,
  type OrganizationChanges,
} from "@/domains/platform/api";
import { roleLabel } from "@/foundation/session/roles";
import { hasCode } from "@/foundation/platform-client";
import { WriteOnlyNote } from "@/domains/platform/chrome";
import {
  CONTRACT_DATES_OUT_OF_ORDER,
  ORG_TYPES,
  asContractDate,
  contractDatesError,
  misfitMembers,
  pageOf,
} from "@/domains/platform/support";

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
  // Members a type change would leave in a role that belongs to another kind of organisation.
  const [misfits, setMisfits] = useState<Membership[] | null>(null);
  const [shownPages, setShownPages] = useState(1);

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

  const changes: OrganizationChanges = { name: name.trim(), org_type: orgType };

  /** Saving a new type first checks who it would strand, and asks before going on. */
  const save = async () => {
    if (orgType === organization.org_type) return commit(changes, "Details saved");
    setBusy(true);
    setError(null);
    try {
      const stranded = misfitMembers(await listAllOrgMemberships(organization.slug), orgType);
      if (stranded.length > 0) {
        setShownPages(1);
        setMisfits(stranded);
        setBusy(false);
        return;
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause : new Error(String(cause)));
      setBusy(false);
      return;
    }
    setBusy(false);
    return commit(changes, "Details saved");
  };

  const dirty = changes.name !== organization.name || changes.org_type !== organization.org_type;

  return (
    <div className="grid items-start gap-6 lg:grid-cols-2">
      <Panel title="Details">
        <div className="flex flex-col gap-3">
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
            hint="Part of the web address of every page in this organisation. It cannot be changed."
          />

          <Select
            label="Type"
            value={orgType}
            onChange={(event) => {
              setOrgType(event.target.value);
              setMisfits(null);
            }}
            disabled={busy}
            hint="Which version of the site this organisation’s members see when they sign in."
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

          {misfits ? (
            <Alert tone="warning">
              <p className="mb-2">
                {misfits.length} {misfits.length === 1 ? "member has a role" : "members have roles"} that
                do not belong in a {orgType} organisation. They keep the role until someone changes it.
              </p>
              <ul className="mb-2 list-disc pl-5">
                {pageOf(misfits, shownPages).map((member) => (
                  <li key={member.id}>
                    {member.email ?? "Unnamed"} · {roleLabel(member.role)}
                  </li>
                ))}
              </ul>
              {pageOf(misfits, shownPages).length < misfits.length ? (
                <Button variant="ghost" size="sm" onClick={() => setShownPages(shownPages + 1)}>
                  Show more
                </Button>
              ) : null}
            </Alert>
          ) : null}

          <div className="flex justify-end gap-2">
            {misfits ? (
              <Button variant="ghost" disabled={busy} onClick={() => setMisfits(null)}>
                Cancel
              </Button>
            ) : null}
            <Button
              disabled={busy || !dirty || !name.trim()}
              onClick={() => (misfits ? commit({ name: name.trim(), org_type: orgType }, "Details saved").then(() => setMisfits(null)) : save())}
            >
              {busy ? "Saving…" : misfits ? "Change type anyway" : "Save"}
            </Button>
          </div>
        </div>
      </Panel>

      <div className="flex flex-col gap-6">
        <ContractDates organization={organization} onChanged={onChanged} />
        <StaffMfaPolicy organization={organization} onChanged={onChanged} />
      </div>
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
      <div className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
        <p className="text-osce-body text-ink">
          {required
            ? "Staff must sign in with a password and an authenticator code."
            : "Staff may sign in with a password alone. Each person can still turn two-factor sign-in on for themselves."}
        </p>
        <p className="text-osce-meta text-ink-subtle">
          Takes effect the next time each person signs in with a password. Anyone without an authenticator app sets one up then. Signing in through the organisation&rsquo;s own login is not affected.
        </p>
        <div className="flex justify-end">
          <Button
            variant={required ? "secondary" : "primary"}
            disabled={busy}
            onClick={() => toggle()}
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
  onChanged,
}: {
  organization: Organization;
  onChanged: (updated: Organization) => void;
}) {
  const toast = useToast();
  const stored = {
    startsAt: contractInputValue(organization.contract_starts_at),
    endsAt: contractInputValue(organization.contract_ends_at),
  };
  const [startsAt, setStartsAt] = useState(stored.startsAt);
  const [endsAt, setEndsAt] = useState(stored.endsAt);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [refusedOrder, setRefusedOrder] = useState(false);
  const orderError =
    contractDatesError(startsAt, endsAt, stored) ??
    (refusedOrder ? CONTRACT_DATES_OUT_OF_ORDER : null);

  const commit = async (changes: OrganizationChanges, done: string) => {
    setBusy(true);
    setError(null);
    setRefusedOrder(false);
    try {
      onChanged(await updateOrganization(organization.slug, changes));
      toast.success(done);
    } catch (cause) {
      // The API's code, never its message, says which field to blame.
      if (hasCode(cause, "contract_dates_out_of_order")) setRefusedOrder(true);
      else setError(cause instanceof Error ? cause : new Error(String(cause)));
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    const changes: OrganizationChanges = {};
    if (startsAt) changes.contract_starts_at = asContractDate(startsAt);
    if (endsAt) changes.contract_ends_at = asContractDate(endsAt);
    if (Object.keys(changes).length === 0) return;
    void commit(changes, "Contract dates saved");
  };

  return (
    <Panel
      title="Contract"
      description="When this organisation's access starts, and when it lapses."
    >
      <div className="flex flex-col gap-3">
        {error ? <Alert tone="danger">{errorMessage(error)}</Alert> : null}
        {!organization.contract_starts_at && !organization.contract_ends_at ? (
          <WriteOnlyNote>
            No contract dates have been set yet. Any field you leave blank stays as it is when you save.
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
          error={orderError}
          hint="Access ends at midnight as this day begins. When the contract ends, the organisation is suspended."
        />

        <div className="flex flex-wrap justify-end gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={busy}
            onClick={() =>
              commit(
                { contract_starts_at: null, contract_ends_at: null },
                "Contract dates cleared",
              )
            }
          >
            Clear both dates
          </Button>
          <Button
            disabled={busy || (!startsAt && !endsAt) || orderError !== null}
            onClick={save}
          >
            {busy ? "Saving…" : "Save dates"}
          </Button>
        </div>
      </div>
    </Panel>
  );
}
