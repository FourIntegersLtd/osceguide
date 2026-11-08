import { workspaceBasePath, type Workspace } from "@/foundation/routing";

/** The one name for the console row, in the menu and in the closed switcher. */
export const PLATFORM_CONSOLE_NAME = "Platform console";

/**
 * A place the switcher can move to. `key` is not a slug: workspace keys and the
 * console key live in separate namespaces, so an organisation slugged "staff"
 * can never be mistaken for the console.
 */
export interface SwitchTarget {
  key: string;
  /** What the token is re-minted for; `null` is the person's own practice. */
  orgSlug: string | null;
  href: string;
}

const CONSOLE_KEY = "console";

export function workspaceTarget(workspace: Workspace): SwitchTarget {
  return { key: `workspace:${workspace.slug}`, orgSlug: workspace.orgSlug, href: workspaceBasePath(workspace) };
}

/** The console is nobody's organisation, so the token goes back to the person's own workspace. */
export const CONSOLE_TARGET: SwitchTarget = { key: CONSOLE_KEY, orgSlug: null, href: "/staff" };

/** The key of where the person is now; `null` current is the console. */
export function currentTargetKey(current: Workspace | null): string {
  return current ? workspaceTarget(current).key : CONSOLE_KEY;
}
