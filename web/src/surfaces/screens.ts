import type { Surface } from "@/capabilities";
import type { ScreenMap, ScreenName, SurfaceManifest } from "@/surfaces/contract";
import { assessScreens } from "@/surfaces/assess/screens";
import { partnerScreens } from "@/surfaces/partner/screens";
import { platformScreens } from "@/surfaces/platform/screens";
import { trainScreens } from "@/surfaces/train/screens";

/**
 * What each arm renders at each arm-owned page.
 *
 * Kept apart from `registry.ts` so the manifests stay free of React: that is
 * what lets the registry test assert the whole shape of the product's
 * navigation without a renderer. This file is the other half, and it is
 * deliberately nothing but a lookup.
 *
 * Hire is absent on purpose. It declares `screensFrom: "assess"`, and
 * `screensFor` follows that, so there is one screen map for the two arms
 * rather than two that drift.
 */
const OWN_SCREENS: Partial<Record<Surface, ScreenMap>> = {
  train: trainScreens,
  assess: assessScreens,
  partner: partnerScreens,
  platform: platformScreens,
};

export function screensFor(manifest: SurfaceManifest): ScreenMap {
  const id = manifest.screensFrom ?? manifest.id;
  return OWN_SCREENS[id] ?? {};
}

export function screenComponent(manifest: SurfaceManifest, name: ScreenName) {
  return screensFor(manifest)[name];
}
