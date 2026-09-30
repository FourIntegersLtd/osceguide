import { LuFileText } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * What was actually said.
 *
 * Every attempt has one, whoever sat it and wherever. A candidate reads their
 * own back; an examiner reads a candidate's while marking. Same screen, and
 * the API decides which transcripts a person may open.
 *
 * Not in the navigation, because in the product it is not a destination: the
 * transcript is the consultation screen's right-hand panel once the
 * consultation is over, and "Load Previous" there is what reaches this list.
 * A sidebar entry made it look like a section of its own.
 */
export const transcriptsCapability: CapabilityModule = {
  id: "transcripts",
  title: "Transcripts",
  description: "Read back what was said in a consultation.",
  surfaces: ["train", "assess"],
  permission: null,
  path: "/transcripts",
  icon: LuFileText,
  hidden: true,
};
