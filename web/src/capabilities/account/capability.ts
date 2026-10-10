import { LuSettings } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * The person, rather than the work: profile, password, access and receipts.
 *
 * Mounted on every arm because everybody using the product is a person with an
 * account, whichever workspace they are standing in. The retiring client had
 * settings under the consumer arm only, so an institution's supervisor had no
 * way to change their own password.
 */
export const accountCapability: CapabilityModule = {
  id: "account",
  title: "Settings",
  description: "Your profile, password, access and receipts.",
  surfaces: ["train", "assess", "hire", "partner", "platform"],
  permission: null,
  section: "general",
  path: "/settings",
  icon: LuSettings,
};
