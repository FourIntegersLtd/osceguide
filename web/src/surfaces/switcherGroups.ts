import type { Workspace } from "@/foundation/routing";

export type SwitcherGroup = { label: string | null; items: Workspace[] };

/**
 * The switcher's menu: your own practice and institutions first, employer
 * workspaces under a "Hiring" heading, so a person who works in hire (or staff
 * testing it) can find the exam-mode workspace that hires.
 */
export function switcherGroups(workspaces: readonly Workspace[]): SwitcherGroup[] {
  const hiring = workspaces.filter((workspace) => workspace.kind === "employer");
  const rest = workspaces.filter((workspace) => workspace.kind !== "employer");
  const groups: SwitcherGroup[] = [{ label: null, items: rest }];
  if (hiring.length > 0) groups.push({ label: "Hiring", items: hiring });
  return groups.filter((group) => group.items.length > 0);
}
