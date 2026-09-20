import type { ComponentType } from "react";
import type { Surface } from "@/capabilities";
import type { SurfaceManifest } from "@/surfaces/contract";
import { TrainNavFooter } from "@/surfaces/train/TrainNavFooter";

/**
 * Nav footers per arm — kept out of `screens.ts` so the workspace shell does
 * not static-import every arm's screen map just to render a footer.
 */
const NAV_FOOTERS: Partial<Record<Surface, ComponentType>> = {
  train: TrainNavFooter,
};

export function navFooterFor(manifest: SurfaceManifest): ComponentType | undefined {
  return NAV_FOOTERS[manifest.screensFrom ?? manifest.id];
}
