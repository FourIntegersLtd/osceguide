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
  readOrganization,
  readSsoStatus,
  renameOrganization,
  type Organization,
} from "@/domains/assess/api";
import { describeSsoStatus } from "@/domains/assess/settings/ssoStatus";
import { InvoicesTab } from "@/domains/assess/settings/InvoicesPage";
import { RetentionCard } from "@/domains/assess/settings/RetentionCard";
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
  const runsOrg = isOrgSurface(surface) && orgSlug && can(session, "manage_team");

  return (
    <Settings
      extraTabs={
        runsOrg
          ? [
              { id: "organisation", label: "Organisation", panel: (setDirty) => <OrganisationPanel orgSlug={orgSlug} setDirty={setDirty} /> },
              { id: "sso", label: "Single sign-on", panel: () => <SignInPanel orgSlug={orgSlug} /> },
              { id: "provisioning", label: "Provisioning", panel: () => <ScimTokens key={orgSlug} orgSlug={orgSlug} /> },
              { id: "invoices", label: "Invoices", after: true, panel: () => <InvoicesTab orgSlug={orgSlug} /> },
            ]
          : []
      }
    />
  );
}

/** The organisation's name, which its admin may change; the web address is fixed and changes go through support. */
function OrganisationPanel({ orgSlug, setDirty }: { orgSlug: string; setDirty: (dirty: boolean) => void }) {
  const state = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  return (
    <AsyncBoundary state={state}>
      {(org) => (
        <>
          <RenameForm key={org.name} org={org} onSaved={state.reload} setDirty={setDirty} />
          <RetentionCard org={org} onSaved={state.reload} />
        </>
      )}
    </AsyncBoundary>
  );
}

function RenameForm({ org, onSaved, setDirty }: { org: Organization; onSaved: () => void; setDirty: (dirty: boolean) => void }) {
  const [name, setName] = useState(org.name);
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const changed = name.trim() !== "" && name.trim() !== org.name;

  // An edited, unsaved name arms the tab strip's "Leave without saving?" guard.
  useDirtyGuard(changed, setDirty);

  async function save() {
    setBusy(true);
    setFailure(null);
    try {
      await renameOrganization(org.slug, name.trim());
      onSaved();
    } catch (cause) {
      setFailure(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <SettingsCard title="Organisation" lead="The web address is fixed. Contact support to change it.">
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
      </div>
      <button type="button" className={cn(boardBtn("primary"), "self-start")} onClick={save} disabled={!changed || busy}>
        {busy ? "Saving…" : "Save name"}
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
  return (
    <>
      <SettingsCard title="Single sign-on" lead="OSCE Guide sets this up with you. Contact support to change it.">
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
      <SettingsCard title="Two-step sign-in for staff">
        <AsyncBoundary state={state}>
          {(org) => (
            <StateRow first>
              <span className="min-w-0 flex-1">
                {org.require_staff_mfa ? "Staff must confirm a code as well as a password." : "Staff sign in with a password alone."}
              </span>
              <Chip tone={org.require_staff_mfa ? "ok" : "neutral"}>{org.require_staff_mfa ? "Required" : "Not required"}</Chip>
            </StateRow>
          )}
        </AsyncBoundary>
      </SettingsCard>
    </>
  );
}

const SSO_TONE: Record<"success" | "neutral" | "warning", BoardChipTone> = { success: "ok", neutral: "neutral", warning: "warn" };
