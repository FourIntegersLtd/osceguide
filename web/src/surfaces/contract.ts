import type { ComponentType, ReactNode } from "react";
import type { Surface } from "@/capabilities";
import type { Permission } from "@/foundation/session";
import type { Workspace, WorkspaceKind } from "@/foundation/routing";

/**
 * A page that means something different depending on which arm you are in.
 *
 * `/app/me/dashboard` and `/app/kings/dashboard` are one route file. What it
 * renders comes from the arm's screen map, so the route file never branches on
 * the arm and adding an arm adds no route files at all.
 *
 * Capability pages — study material, discussion, stations, help — are **not**
 * here. They are the same component everywhere by construction and are mounted
 * from `capabilities/registry.ts`.
 */
export type ScreenName =
  // Every arm has a landing screen; none of them are the same screen.
  | "dashboard"
  // Consumer
  | "mocks"
  | "mockDetail"
  | "mockStation"
  | "attempt"
  | "access"
  // Institution and employer
  | "sittings"
  | "sittingDetail"
  | "sittingResults"
  | "newSitting"
  | "newCircuit"
  | "circuitConsole"
  | "live"
  | "slotReview"
  | "trainees"
  | "team"
  | "myTraining"
  | "myResult"
  // Partner
  | "reporting"
  // Staff console
  | "organizations"
  | "users";

export interface NavItem {
  key: string;
  label: string;
  href: string;
  icon?: ComponentType<{ className?: string }>;
}

export interface NavContext {
  workspace: Workspace;
  /** From `/me/capabilities`. Navigation is filtered by the backend's answer. */
  can: (permission: Permission) => boolean;
  /** Prefix a surface-relative path, e.g. `href("/sittings")`. */
  href: (path: string) => string;
}

/**
 * An arm, declared as data.
 *
 * Arms used to be a string in a union plus a `switch` plus a hand-written
 * shell, so adding one touched four unrelated files and nothing checked that
 * you had. A capability has had a manifest and a registry since the beginning;
 * this gives an arm the same treatment.
 *
 * Deliberately free of React components. Everything here can be read, tested
 * and reasoned about without rendering anything, which is why the registry
 * test can assert the whole shape of the product's navigation. The components
 * live in `screens.tsx` and `shell.tsx` beside it.
 */
export interface SurfaceManifest {
  id: Surface;
  /** Shown in the shell's title and in the workspace switcher. */
  label: string;
  /**
   * Which kinds of workspace mount this arm. `surfaceForWorkspace` inverts
   * this, and `registry.test.ts` fails if two arms claim the same kind.
   */
  workspaceKinds: readonly WorkspaceKind[];
  /** The arm's own destinations. Capability destinations are appended. */
  nav: (context: NavContext) => NavItem[];
  /** The arm-owned pages this arm answers. A page not listed here is a 404. */
  screenNames: readonly ScreenName[];
  /**
   * Render another arm's screens rather than declaring your own.
   *
   * Hire is the reason this exists: an employer is an organisation running an
   * exam-mode sitting, so it is the Assess screens with different wording, not
   * a second implementation. Saying so in data means the registry test can
   * check it, rather than it being a promise in a comment.
   */
  screensFrom?: Surface;
}

/**
 * What every arm-owned screen is given.
 *
 * One shape for all of them so the route files stay uniform: a page reads its
 * params, hands them over, and renders nothing itself.
 */
export interface ScreenProps {
  workspace: Workspace;
  /** Route parameters below the workspace, e.g. `{ sittingId }`. */
  params?: Record<string, string>;
}

export type ScreenMap = Partial<Record<ScreenName, ComponentType<ScreenProps>>>;

export interface ShellProps {
  workspace: Workspace;
  children: ReactNode;
}
