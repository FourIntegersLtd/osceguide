import type { AssessWords } from "@/capabilities/assess-words";
import { say } from "@/domains/assess/roster/rosterWords";
import { CANDIDATES_DESC } from "@/domains/assess/people/candidatesView";

export type PeopleTab = "trainees" | "staff" | "groups" | "access" | "history";

/**
 * The People tabs, in the order of the board. Staff, Exam access and History are the
 * admin's (`manage_team`); a supervisor reads Trainees and Groups, with no write buttons.
 */
export function peopleTabs(
  can: { manageTeam: boolean },
  words: AssessWords,
): { key: PeopleTab; label: string }[] {
  const tabs: { key: PeopleTab; label: string }[] = [
    { key: "trainees", label: words.Trainees },
    { key: "staff", label: words.hiring ? words.Supervisors : "Staff" },
    { key: "groups", label: say(words, "Groups and year groups") },
    { key: "access", label: "Exam access" },
    { key: "history", label: words.hiring ? "Activity" : "History" },
  ];
  return can.manageTeam ? tabs : tabs.filter((tab) => tab.key === "trainees" || tab.key === "groups");
}

/** `/trainees` opens on Trainees; `/team` still resolves, on Staff. */
export function initialPeopleTab(route: "trainees" | "team"): PeopleTab {
  return route === "team" ? "staff" : "trainees";
}

export type PeopleHeader = {
  eyebrow: string;
  title: string;
  desc: string;
  /** The one primary: what it says, and which add flow it opens. */
  action: { label: string; opens: "trainees" | "staff" };
};

const ASSESSORS_DESC = "The staff who mark candidates and run rotations, and who else can manage this account.";

/**
 * The page's head for the open tab. An institution has one People page; a hire workspace has two
 * pages in one component, Candidates and Assessors, each with its own words and its one primary.
 */
export function peopleHeader(tab: PeopleTab, words: AssessWords, orgName: string): PeopleHeader {
  if (!words.hiring) {
    return {
      eyebrow: "Organise",
      title: words.People,
      desc: `Everyone in ${orgName}. ${words.Trainees} sit ${words.sittings}; staff (supervisors and admins) run circuits and mark them.`,
      action: { label: words.addPeople, opens: tab === "staff" ? "staff" : "trainees" },
    };
  }
  const assessors = tab === "staff" || tab === "history";
  return {
    eyebrow: orgName,
    title: assessors ? words.Supervisors : words.People,
    desc: assessors ? ASSESSORS_DESC : CANDIDATES_DESC,
    action: assessors ? { label: "Invite an assessor", opens: "staff" } : { label: words.addPeople, opens: "trainees" },
  };
}
