import { createLocalPreference } from "@/foundation/hooks/createLocalPreference";

export type SideTab = "covered" | "cues";

/** The tab the candidate last chose in the live column, or null if they never have. */
export const sideTab = createLocalPreference<SideTab | null>({
  key: "osce_live_side_tab",
  fallback: null,
  decode: (stored) => (stored === "covered" || stored === "cues" ? stored : null),
  encode: (value) => value,
});

/** The "Camera on for cues" line shows when the camera runs and the live cues tab is not already showing it. */
export function showCameraLine({ cameraOn, collapsed, tab }: { cameraOn: boolean; collapsed: boolean; tab: SideTab }): boolean {
  return cameraOn && (collapsed || tab === "covered");
}
