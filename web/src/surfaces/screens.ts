import type { ComponentType } from "react";
import type { Surface } from "@/capabilities";
import type { ScreenMap, ScreenName, ScreenProps, SurfaceManifest } from "@/surfaces/contract";

/**
 * What each arm renders at each arm-owned page.
 *
 * Kept apart from `registry.ts` so the manifests stay free of React: that is
 * what lets the registry test assert the whole shape of the product's
 * navigation without a renderer. This file is the other half, and it is
 * deliberately nothing but a lookup.
 *
 * Screen maps are loaded per arm on demand so dev compiles do not pull every
 * domain into the workspace layout chunk.
 *
 * Hire is absent on purpose. It declares `screensFrom: "assess"`, and
 * `screensFor` follows that, so there is one screen map for the two arms
 * rather than two that drift.
 */
const SCREEN_LOADERS: Partial<Record<Surface, () => Promise<ScreenMap>>> = {
  train: () => import("@/surfaces/train/screens").then((mod) => mod.trainScreens),
  assess: () => import("@/surfaces/assess/screens").then((mod) => mod.assessScreens),
  partner: () => import("@/surfaces/partner/screens").then((mod) => mod.partnerScreens),
};

const screenMapCache = new Map<Surface, Promise<ScreenMap>>();

function screenMapKey(manifest: SurfaceManifest): Surface {
  return manifest.screensFrom ?? manifest.id;
}

export function loadScreensFor(manifest: SurfaceManifest): Promise<ScreenMap> {
  const id = screenMapKey(manifest);
  const loader = SCREEN_LOADERS[id];
  if (!loader) return Promise.resolve({});

  const cached = screenMapCache.get(id);
  if (cached) return cached;

  const pending = loader();
  screenMapCache.set(id, pending);
  return pending;
}

export async function loadScreenComponent(
  manifest: SurfaceManifest,
  name: ScreenName,
): Promise<ComponentType<ScreenProps> | undefined> {
  const map = await loadScreensFor(manifest);
  return map[name];
}

/** @deprecated Prefer `loadScreensFor` — sync lookup forces every arm's map into the bundle. */
export async function screensFor(manifest: SurfaceManifest,
): Promise<ScreenMap> {
  return loadScreensFor(manifest);
}

/** @deprecated Prefer `loadScreenComponent`. */
export async function screenComponent(
  manifest: SurfaceManifest,
  name: ScreenName,
): Promise<ComponentType<ScreenProps> | undefined> {
  return loadScreenComponent(manifest, name);
}
