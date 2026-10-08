"use client";

import { AsyncBoundary, Badge, Input, Panel } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { Settings } from "@/capabilities/account";
import { readOrganization } from "@/domains/assess/api";
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
  const runsOrg = (surface === "assess" || surface === "hire") && orgSlug && can(session, "manage_team");

  return (
    <Settings
      extraTabs={
        runsOrg
          ? [
              { id: "organisation", label: "Organisation", panel: <OrganisationPanel orgSlug={orgSlug} /> },
              { id: "sso", label: "Single sign-on", panel: <SignInPanel orgSlug={orgSlug} /> },
              { id: "provisioning", label: "Provisioning", panel: <ScimTokens orgSlug={orgSlug} /> },
            ]
          : []
      }
    />
  );
}

/**
 * The organisation's name and address, read-only.
 *
 * There is no route to change an organisation (U-17 in the backlog), so the
 * fields are shown as they are and changes go through support.
 */
function OrganisationPanel({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  return (
    <AsyncBoundary state={state}>
      {(org) => (
        <Panel title="Organisation" description="Contact support to change these.">
          <div className="flex max-w-xl flex-col gap-4">
            <Input label="Name" readOnly value={org.name} />
            <Input label="Web address" readOnly value={`/${org.slug}`} />
          </div>
        </Panel>
      )}
    </AsyncBoundary>
  );
}

/**
 * How the organisation's people sign in.
 *
 * Single sign-on is set up by OSCE Guide staff, and its routes answer only to
 * them, so an organisation cannot yet see whether it is connected. What it
 * can see is its two-step rule, which is on the organisation itself.
 */
function SignInPanel({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  return (
    <div className="flex flex-col gap-5">
      <Panel title="Single sign-on">
        <p className="max-w-xl text-osce-body text-b2b-mid">
          Your staff and trainees can sign in with your organisation&apos;s own accounts. OSCE Guide sets this up
          with you, and whether it is connected cannot be shown here yet. Contact support to set it up or change it.
        </p>
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
