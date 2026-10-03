"use client";

import { useState } from "react";
import { Alert, AsyncBoundary, Badge, Button, Input } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { Settings } from "@/capabilities/account";
import { readOrganization, type Organization } from "@/domains/assess/api";
import { Panel } from "@/domains/assess/programmes/parts";

/**
 * Settings, with the organisation's own tabs for the people who run it.
 *
 * The account capability knows nothing about institutions, so the two extra
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
            ]
          : []
      }
    />
  );
}

/**
 * The organisation's name, contact address and logo.
 *
 * The name is read from `GET /orgs/{slug}`. There is no route to change it,
 * and the organisation has no contact email or logo column, so saving says
 * so and stores nothing.
 */
function OrganisationPanel({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => readOrganization(orgSlug, signal), [orgSlug]);
  return <AsyncBoundary state={state}>{(org) => <OrganisationForm org={org} />}</AsyncBoundary>;
}

function OrganisationForm({ org }: { org: Organization }) {
  const [name, setName] = useState(org.name);
  const [contactEmail, setContactEmail] = useState("");
  const [notSaved, setNotSaved] = useState(false);

  return (
    <Panel title="Organisation">
      <form
        className="flex max-w-xl flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          setNotSaved(true);
        }}
      >
        <Input label="Name" required value={name} onChange={(event) => setName(event.target.value)} />
        <Input
          label="Contact email"
          type="email"
          value={contactEmail}
          onChange={(event) => setContactEmail(event.target.value)}
          hint="Not stored yet: the organisation has no contact address on the API."
        />
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-osce-meta font-medium text-b2b-headline">Logo</p>
            <p className="text-osce-meta text-b2b-mid">Shown on results and certificates.</p>
          </div>
          <Button themeType="b2b" variant="secondary" size="sm" disabled title="Not connected yet">
            Upload
          </Button>
        </div>
        {notSaved ? (
          <Alert tone="warning" title="Nothing was saved">
            Changing an organisation&apos;s details needs an API route that does not exist yet.
          </Alert>
        ) : null}
        <div className="flex justify-end">
          <Button themeType="b2b" variant="commit" type="submit" disabled={name.trim().length === 0}>
            Save
          </Button>
        </div>
      </form>
    </Panel>
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
