"use client";

import { isOrgSurface } from "@/capabilities/surface";
import { useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Input, Panel } from "@/foundation/ui";
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
import { InvoicesPanel } from "@/domains/assess/settings/InvoicesPanel";
import { ScimTokens } from "@/domains/assess/settings/ScimTokens";

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
              { id: "invoices", label: "Invoices", after: true, panel: (setDirty) => <InvoicesPanel key={orgSlug} orgSlug={orgSlug} setDirty={setDirty} /> },
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
      {(org) => <RenameForm key={org.name} org={org} onSaved={state.reload} setDirty={setDirty} />}
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
    <Panel title="Organisation" description="The web address is fixed. Contact support to change it.">
      <div className="flex max-w-xl flex-col gap-4">
        {failure ? <Alert tone="danger">{failure}</Alert> : null}
        <Input label="Name" value={name} maxLength={200} onChange={(event) => setName(event.target.value)} />
        <Input label="Web address" readOnly value={`/${org.slug}`} />
        <div>
          <Button onClick={save} disabled={!changed || busy}>
            {busy ? "Saving…" : "Save name"}
          </Button>
        </div>
      </div>
    </Panel>
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
    <div className="flex flex-col gap-5">
      <Panel title="Single sign-on" description="OSCE Guide sets this up with you. Contact support to change it.">
        <AsyncBoundary state={sso}>
          {(status) => {
            const view = describeSsoStatus(status);
            return (
              <div className="flex items-center justify-between gap-3">
                <p className="max-w-xl text-osce-body text-b2b-mid">{view.detail}</p>
                <Badge variant={view.tone} dot>
                  {view.badge}
                </Badge>
              </div>
            );
          }}
        </AsyncBoundary>
      </Panel>
      <Panel title="Two-step sign-in for staff">
        <AsyncBoundary state={state}>
          {(org) => (
            <div className="flex items-center justify-between gap-3">
              <p className="max-w-xl text-osce-body text-b2b-mid">
                {org.require_staff_mfa
                  ? "Staff must confirm a code as well as a password."
                  : "Staff sign in with a password alone."}
              </p>
              <Badge variant={org.require_staff_mfa ? "success" : "neutral"} dot>
                {org.require_staff_mfa ? "Required" : "Not required"}
              </Badge>
            </div>
          )}
        </AsyncBoundary>
      </Panel>
    </div>
  );
}
