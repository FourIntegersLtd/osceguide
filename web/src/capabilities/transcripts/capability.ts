import { LuFileText } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * What was actually said.
 *
 * Every attempt has one, whoever sat it and wherever. A candidate reads their
 * own back; an examiner reads a candidate's while marking. Same screen, and
 * the API decides which transcripts a person may open.
 *
 * Listed in the navigation under Practice, beside the consultation screen's
 * right-hand panel.
 */
export const transcriptsCapability: CapabilityModule = {
  id: "transcripts",
  title: "Transcripts",
  description: "Read back what was said in a consultation.",
  surfaces: ["train", "assess"],
  permission: null,
  section: "practice",
  path: "/transcripts",
  icon: LuFileText,
};
