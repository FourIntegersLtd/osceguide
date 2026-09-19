import { LuStethoscope } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/** The shared station library. Every arm practises from the same one. */
export const stationsCapability: CapabilityModule = {
  id: "stations",
  title: "Stations",
  description: "Browse every scenario published for your exams.",
  surfaces: ["train", "assess", "hire"],
  permission: null,
  path: "/stations",
  icon: LuStethoscope,
};
