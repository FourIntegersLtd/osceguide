import type { ComponentType } from "react";
import type { Surface } from "@/capabilities";
import type { ScreenMap, ScreenName, SurfaceManifest } from "@/surfaces/contract";
import { TrainNavFooter } from "@/surfaces/train/TrainNavFooter";
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

/**
 * What an arm renders under its navigation, if anything.
 *
 * Here rather than on the manifest for the same reason the screens are: a
 * component in the manifest would put React in a file the registry test reads
 * without a renderer. Only the consumer arm has one, where it carries the
 * upgrade button, the person's name and which exam they are sitting.
 */
const NAV_FOOTERS: Partial<Record<Surface, ComponentType>> = {
  train: TrainNavFooter,
};

export function navFooterFor(manifest: SurfaceManifest): ComponentType | undefined {
  return NAV_FOOTERS[manifest.screensFrom ?? manifest.id];
}
