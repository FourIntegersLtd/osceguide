import { LuStethoscope } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * The shared station library, and the consultation run from it.
 *
 * Every arm practises from the same one. The detail view and the consultation
 * are query parameters on this one path rather than routes of their own, so
 * mounting the library on a fourth arm stays a line in `surfaces` below.
 */
export const stationsCapability: CapabilityModule = {
  id: "stations",
  title: "Stations",
  description: "Browse every scenario published for your exams, and practise one.",
  surfaces: ["train", "assess", "hire"],
  permission: null,
  path: "/stations",
  icon: LuStethoscope,
};
