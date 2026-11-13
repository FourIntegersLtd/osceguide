import { createLocalPreference } from "@/foundation/hooks/createLocalPreference";

export type SideTab = "covered" | "cues";

/** The tab the candidate last chose in the live column, or null if they never have. */
export const sideTab = createLocalPreference<SideTab | null>({
  key: "osce_live_side_tab",
  fallback: null,
  decode: (stored) => (stored === "covered" || stored === "cues" ? stored : null),
  encode: (value) => value,
});
