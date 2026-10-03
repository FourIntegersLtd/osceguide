"use client";

import { useState } from "react";
import { Button, B2CPageHeader, TextLink } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip, type Tab } from "@/domains/assess/team/chrome";
import { MembersPanel } from "@/domains/assess/team/MembersPanel";
import { InvitePanel } from "@/domains/assess/team/InvitePanel";
import { ActivityPanel } from "@/domains/assess/team/ActivityPanel";
import { sectionSubtitle } from "@/domains/assess/team/support";

type Section = "members" | "invite" | "activity";

const TABS: readonly Tab<Section>[] = [
  { key: "members", label: "Members" },
  { key: "invite", label: "Add people" },
  { key: "activity", label: "History" },
];

/**
 * The organisation's staff.
 *
 * Team is who runs the examination; the roster — `/trainees` — is who sits it.
 * The retiring client had both on one screen with two tables, which is why an
 * administrator could revoke a supervisor from a tab headed "Trainees".
 *
 * What may be done here comes from `/me/capabilities`, never from the role
 * string on the membership row: the old B2B client kept its own copy of that
 * policy and offered actions the API then refused.
 */
export function Team({ orgSlug }: { orgSlug: string }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const [section, setSection] = useState<Section>("members");
  const canManage = can(session, "manage_team");

  return (
    <div className="flex flex-col gap-6">
      <B2CPageHeader
        title="Team"
        subtitle={sectionSubtitle(section)}
        action={
          canManage && section === "members" ? (
            <Button themeType="b2b" variant="commit" onClick={() => setSection("invite")}>
              Add people
            </Button>
          ) : null
        }
      />

      <TabStrip tabs={TABS} active={section} onSelect={setSection} label="Team sections" />

      {section === "activity" ? (
        <ActivityPanel orgSlug={orgSlug} />
      ) : section === "members" ? (
        <MembersPanel orgSlug={orgSlug} canManage={canManage} />
      ) : (
        // The members list re-fetches on its own next mount, so nothing here
        // needs to be told a new person was added.
        <InvitePanel orgSlug={orgSlug} canManage={canManage} onInvited={() => {}} />
      )}

      <p className="text-osce-caption text-b2b-mid">
        Looking for the people being examined?{" "}
        <TextLink themeType="b2b" href={hrefFor("/trainees")}>Go to the roster</TextLink>.
      </p>
    </div>
  );
}
