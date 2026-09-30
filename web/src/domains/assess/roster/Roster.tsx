"use client";

import { useState } from "react";
import {
  HiOutlineKey,
  HiOutlineSquares2X2,
  HiOutlineUserGroup,
  HiOutlineUserPlus,
} from "react-icons/hi2";
import { AsyncBoundary, Button, PageHeader, TextLink } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { can, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { TabStrip, type Tab } from "@/domains/assess/team/chrome";
import { listAllTrainees, listCohorts, listTraineeGroups } from "@/domains/assess/roster/api";
import { TraineesPanel } from "@/domains/assess/roster/TraineesPanel";
import { AddTraineePanel } from "@/domains/assess/roster/AddTraineePanel";
import { GroupsPanel } from "@/domains/assess/roster/GroupsPanel";
import { AccessPanel } from "@/domains/assess/roster/AccessPanel";
import { sectionSubtitle } from "@/domains/assess/roster/support";

type Section = "trainees" | "add" | "groups" | "access";

const TABS: readonly Tab<Section>[] = [
  { key: "trainees", label: "Trainees", icon: (props) => <HiOutlineSquares2X2 {...props} /> },
  { key: "add", label: "Add people", icon: (props) => <HiOutlineUserPlus {...props} /> },
  { key: "groups", label: "Groups", icon: (props) => <HiOutlineUserGroup {...props} /> },
  { key: "access", label: "Exam access", icon: (props) => <HiOutlineKey {...props} /> },
];

/**
 * The roster: who the organisation examines.
 *
 * Separate from Team, which is the staff who run the examination. The three
 * lists are loaded once for the whole screen rather than per tab — the old
 * client had each of these as its own route and refetched the roster on every
 * visit — and every write reloads all three, because adding a trainee changes
 * a group's count and granting access changes nothing else on the page.
 */
export function Trainees({ orgSlug }: { orgSlug: string }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const [section, setSection] = useState<Section>("trainees");
  const canManage = can(session, "manage_team");

  const state = useAsync(
    async (signal) => {
      const [trainees, cohorts, groups] = await Promise.all([
        listAllTrainees(orgSlug, signal),
        listCohorts(orgSlug, signal),
        listTraineeGroups(orgSlug, signal),
      ]);
      return { trainees, cohorts: cohorts.items, groups: groups.items };
    },
    [orgSlug],
  );

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {(data) => (
          <>
            <PageHeader
              title="Trainees"
              description={sectionSubtitle(section, {
                trainees: data.trainees.length,
                groups: data.groups.length,
              })}
              actions={
                canManage && section === "trainees" ? (
                  <Button themeType="b2b" variant="commit" onClick={() => setSection("add")}>
                    Add trainees
                  </Button>
                ) : null
              }
            />

            <TabStrip tabs={TABS} active={section} onSelect={setSection} label="Roster sections" />

            {section === "trainees" ? (
              <TraineesPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                canManage={canManage}
                onChanged={state.reload}
              />
            ) : null}

            {section === "add" ? (
              <AddTraineePanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                canManage={canManage}
                onAdded={state.reload}
              />
            ) : null}

            {section === "groups" ? (
              <GroupsPanel
                orgSlug={orgSlug}
                cohorts={data.cohorts}
                groups={data.groups}
                trainees={data.trainees}
                canManage={canManage}
                onChanged={state.reload}
              />
            ) : null}

            {section === "access" ? (
              <AccessPanel orgSlug={orgSlug} trainees={data.trainees} canManage={canManage} />
            ) : null}
          </>
        )}
      </AsyncBoundary>

      <p className="text-osce-caption text-b2b-mid">
        Looking for supervisors and admins?{" "}
        <TextLink themeType="b2b" href={hrefFor("/team")}>
          Go to the team
        </TextLink>
        .
      </p>
    </div>
  );
}
