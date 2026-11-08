"use client";

import { isOrgSurface } from "@/capabilities/surface";
import { useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn } from "@/foundation/ui";
import { Chip, Note } from "@/domains/assess/ui";
import { SettingsCard, StateRow } from "@/domains/assess/settings/SettingsCard";
import { errorMessage, useAsync, useDirtyGuard } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { Settings } from "@/capabilities/account";
import {
  listTrainees,
  readOrganization,
  readSsoStatus,
  updateOrganization,
  type Organization,
} from "@/domains/assess/api";
import { useAssessWords } from "@/capabilities/assess-words";
import { shortDay } from "@/domains/assess/roster/support";
import {
  contactEmailLooksValid,
  organisationChanges,
  organisationFailure,
  organisationLead,
  organisationSaveLabel,
  orgTabLabels,
  planLine,
} from "@/domains/assess/settings/hireSettings";
import { MFA_PILLS_CHANGE, MFA_PILLS_HINT, mfaPills, ssoLead, staffMfaCopy } from "@/domains/assess/settings/signInCopy";
import { describeSsoStatus } from "@/domains/assess/settings/ssoStatus";
import { InvoicesTab } from "@/domains/assess/settings/InvoicesPage";
import { ScimTokens } from "@/domains/assess/settings/ScimTokens";
import { boardBtn, boardInput, boardLabel as labelClass, type BoardChipTone } from "@/foundation/ui/boardKit";

/**
 * Settings, with the organisation's own tabs for the people who run it.
 *
 * The account capability knows nothing about institutions, so the extra
 * tabs are handed to it from here. Everybody else, on every other arm, gets
 * the capability exactly as it was.
 */
export function WorkspaceSettings() {
  const { surface, orgSlug } = useSurface();
  const { session } = useSession();
  const w = useAssessWords();
  const tabLabels = orgTabLabels(w);
  const runsOrg = isOrgSurface(surface) && orgSlug && can(session, "manage_team");

  return (
    <Settings
      extraTabs={
        runsOrg
          ? [
              { id: "organisation", label: "Organisation", panel: (setDirty) => <OrganisationPanel orgSlug={orgSlug} setDirty={setDirty} /> },
              { id: "sso", label: tabLabels.sso, panel: () => <SignInPanel orgSlug={orgSlug} /> },
              { id: "provisioning", label: tabLabels.provisioning, panel: () => <ScimTokens key={orgSlug} orgSlug={orgSlug} /> },
              { id: "invoices", label: "Invoices", after: true, panel: () => <InvoicesTab orgSlug={orgSlug} /> },
            ]
          : []
      }
    />
  );
}

/** The organisation's name, which its admin may change; the web address is fixed and changes go through support. */
function OrganisationPanel({ orgSlug, setDirty }: { orgSlug: string; setDirty: (dirty: boolean) => void }) {
  const hiring = useAssessWords().hiring;
  const state = useAsync(async (signal) => {
    const org = await readOrganization(orgSlug, signal);
    // Seats used = candidates who still have access; only an employer with seats set shows it.
    const used = hiring && org.candidate_seats != null
      ? (await listTrainees(orgSlug, signal, { limit: 1, accessRevoked: false })).total_count ?? null
      : null;
    return { org, used };
  }, [orgSlug, hiring]);
  return (
    <AsyncBoundary state={state}>
      {({ org, used }) => <OrganisationForm key={`${org.name}|${org.contact_email ?? ""}`} org={org} seatsUsed={used} onSaved={state.reload} setDirty={setDirty} />}
    </AsyncBoundary>
  );
}

function OrganisationForm({ org, seatsUsed, onSaved, setDirty }: { org: Organization; seatsUsed: number | null; onSaved: () => void; setDirty: (dirty: boolean) => void }) {
  const w = useAssessWords();
  const hiring = w.hiring;
  const [name, setName] = useState(org.name);
  const [contactEmail, setContactEmail] = useState(org.contact_email ?? "");
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const changes = organisationChanges(org, { name, contactEmail }, w);
  const valid = !hiring || contactEmailLooksValid(contactEmail);

  // An edited, unsaved name or contact arms the tab strip's "Leave without saving?" guard, valid or not.
  useDirtyGuard(changes !== null, setDirty);

  async function save() {
    if (!changes) return;
    setBusy(true);
    setFailure(null);
    try {
      await updateOrganization(org.slug, changes);
      onSaved();
    } catch (cause) {
      setFailure(organisationFailure(cause, changes, errorMessage));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SettingsCard title="Organisation" lead={organisationLead(w)}>
      {failure ? <Note tone="bad" role="alert">{failure}</Note> : null}
      <div className={t.assessFormStack}>
        <div>
          <label htmlFor="org-name" className={labelClass}>Name</label>
          <input id="org-name" className={boardInput} value={name} maxLength={200} onChange={(event) => setName(event.target.value)} />
        </div>
        <div>
          <label htmlFor="org-slug" className={labelClass}>Web address</label>
          <input id="org-slug" className={boardInput} readOnly value={`/${org.slug}`} />
        </div>
        {hiring ? (
          <>
            <div>
              <label htmlFor="org-contact" className={labelClass}>Contact email</label>
              <input id="org-contact" type="email" className={boardInput} value={contactEmail} maxLength={254} onChange={(event) => setContactEmail(event.target.value)} aria-invalid={!valid} />
            </div>
            <StateRow first>
              <span className="min-w-0 flex-1">Plan</span>
              <span>{planLine(org, shortDay, seatsUsed)}</span>
            </StateRow>
          </>
        ) : null}
      </div>
      <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={save} disabled={changes === null || !valid || busy}>
        {busy ? "Saving…" : organisationSaveLabel(w)}
      </button>
    </SettingsCard>
  );
}

/**
 * How the organisation's people sign in.
 *
 * Single sign-on is set up by OSCE Guide staff; the organisation sees whether
 * it is connected, read-only, beside its own two-step rule.
 */
function SignInPanel({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  const sso = useAsync((signal) => readSsoStatus(orgSlug, signal), [orgSlug]);
  const w = useAssessWords();
  return (
    <>
      <SettingsCard title="Single sign-on" lead={ssoLead(w)}>
        <AsyncBoundary state={sso}>
          {(status) => {
            const view = describeSsoStatus(status);
            return (
              <StateRow first>
                <span className="min-w-0 flex-1">{view.detail}</span>
                <Chip tone={SSO_TONE[view.tone]}><span aria-hidden>●</span> {view.badge}</Chip>
              </StateRow>
            );
          }}
        </AsyncBoundary>
      </SettingsCard>
      <SettingsCard title={staffMfaCopy(true, w).title}>
        <AsyncBoundary state={state}>
          {(org) => (
            <>
              <StateRow first>
                <span className="min-w-0 flex-1">
                  {staffMfaCopy(org.require_staff_mfa, w).detail}
                </span>
                {w.hiring ? null : <Chip tone={org.require_staff_mfa ? "ok" : "neutral"}>{org.require_staff_mfa ? "Required" : "Not required"}</Chip>}
              </StateRow>
            {w.hiring ? (
              <>
                <div className="flex flex-wrap gap-2" role="group" aria-label="Two-step sign-in">
                  {mfaPills(org.require_staff_mfa).map((pill) => (
                    <Chip key={pill.label} tone={pill.on ? "ok" : "neutral"}>{pill.label}</Chip>
                  ))}
                </div>
                <p className={cn(t.assessMeta, "m-0")}>{MFA_PILLS_HINT} {MFA_PILLS_CHANGE}</p>
              </>
              ) : null}
            </>
          )}
        </AsyncBoundary>
      </SettingsCard>
    </>
  );
}

const SSO_TONE: Record<"success" | "neutral" | "warning", BoardChipTone> = { success: "ok", neutral: "neutral", warning: "warn" };
