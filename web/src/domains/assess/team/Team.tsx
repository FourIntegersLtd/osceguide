"use client";

import { useState } from "react";
import { HiOutlineClock, HiOutlineSquares2X2, HiOutlineUserPlus } from "react-icons/hi2";
import { AsyncBoundary, Button, PageHeader, TextLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip, type Tab } from "@/domains/assess/team/chrome";
import { listAllMemberships } from "@/domains/assess/team/api";
import { MembersPanel } from "@/domains/assess/team/MembersPanel";
import { InvitePanel } from "@/domains/assess/team/InvitePanel";
import { ActivityPanel } from "@/domains/assess/team/ActivityPanel";
import { sectionSubtitle } from "@/domains/assess/team/support";

type Section = "members" | "invite" | "activity";

const TABS: readonly Tab<Section>[] = [
  { key: "members", label: "Members", icon: (props) => <HiOutlineSquares2X2 {...props} /> },
  { key: "invite", label: "Add people", icon: (props) => <HiOutlineUserPlus {...props} /> },
  { key: "activity", label: "History", icon: (props) => <HiOutlineClock {...props} /> },
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
  const state = useAsync((signal) => listAllMemberships(orgSlug, signal), [orgSlug]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Team"
        description={sectionSubtitle(section)}
        actions={
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
      ) : (
        <AsyncBoundary state={state}>
          {(members) =>
            section === "members" ? (
              <MembersPanel
                orgSlug={orgSlug}
                members={members}
                canManage={canManage}
                onChanged={state.reload}
              />
            ) : (
              <InvitePanel orgSlug={orgSlug} canManage={canManage} onInvited={state.reload} />
            )
          }
        </AsyncBoundary>
      )}

      <p className="text-osce-caption text-b2b-mid">
        Looking for the people being examined?{" "}
        <TextLink themeType="b2b" href={hrefFor("/trainees")}>Go to the roster</TextLink>.
      </p>
    </div>
  );
}
