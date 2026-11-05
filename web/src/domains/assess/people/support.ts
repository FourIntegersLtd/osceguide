import type { AssessWords } from "@/domains/assess/vocabulary";

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
    { key: "staff", label: "Staff" },
    { key: "groups", label: "Groups and year groups" },
    { key: "access", label: "Exam access" },
    { key: "history", label: "History" },
  ];
  return can.manageTeam ? tabs : tabs.filter((tab) => tab.key === "trainees" || tab.key === "groups");
}

/** `/trainees` opens on Trainees; `/team` still resolves, on Staff. */
export function initialPeopleTab(route: "trainees" | "team"): PeopleTab {
  return route === "team" ? "staff" : "trainees";
}
