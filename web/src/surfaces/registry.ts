import type { Surface } from "@/capabilities";
import type { Workspace, WorkspaceKind } from "@/foundation/routing";
import type { SurfaceManifest } from "@/surfaces/contract";
import { assessSurface } from "@/surfaces/assess/surface";
import { hireSurface } from "@/surfaces/hire/surface";
import { partnerSurface } from "@/surfaces/partner/surface";
import { platformSurface } from "@/surfaces/platform/surface";
import { trainSurface } from "@/surfaces/train/surface";

/**
 * Every arm, declared.
 *
 * `Record<Surface, SurfaceManifest>` rather than an array: adding a name to
 * the `Surface` union without adding its manifest is a compile error here,
 * which is the whole reason arms are declared at all. Before this, an arm was
 * a string in a union plus a `switch` plus a hand-written shell, and nothing
 * checked that the three agreed.
 *
 * This module holds no React. That is what lets `registry.test.ts` assert the
 * whole shape of the product's navigation — which arms exist, which workspaces
 * reach them, what each one's menu says and who is allowed to see each item —
 * without rendering anything.
 */
export const SURFACE_MANIFESTS: Record<Surface, SurfaceManifest> = {
  train: trainSurface,
  assess: assessSurface,
  hire: hireSurface,
  partner: partnerSurface,
  platform: platformSurface,
};

export const ALL_SURFACES: readonly SurfaceManifest[] = Object.values(SURFACE_MANIFESTS);

/**
 * Which arm a workspace is seen through.
 *
 * This is the one decision that used to be spread across a route prefix, a
 * redirect in the front door and a `switch` over base paths. A workspace's
 * kind picks its arm; nothing else does.
 */
export function surfaceForWorkspace(workspace: Workspace): SurfaceManifest {
  return surfaceForKind(workspace.kind);
}

export function surfaceForKind(kind: WorkspaceKind): SurfaceManifest {
  const found = ALL_SURFACES.find((manifest) => manifest.workspaceKinds.includes(kind));
  // `workspaceKind()` already narrows an unknown `org_type` to `institution`,
  // so this is unreachable in practice — but an unmapped kind must not blank
  // the screen, and the institution shell is the most restrictive one.
  return found ?? assessSurface;
}

export function surfaceManifest(id: Surface): SurfaceManifest {
  return SURFACE_MANIFESTS[id];
}

/** Whether this arm answers this page, or renders a 404 for it. */
export function ownsScreen(manifest: SurfaceManifest, screen: string): boolean {
  return (manifest.screenNames as readonly string[]).includes(screen);
}
