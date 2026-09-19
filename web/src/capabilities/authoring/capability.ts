import { LuPencilRuler } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Writing the material an exam is made of.
 *
 * Stations and their versions, station templates, feedback templates, rubrics,
 * exams and programmes. One implementation for three arms: the backend serves
 * the same shapes under `/orgs/{slug}/…` and `/platform/…`, so the scope comes
 * from `SurfaceContext` and nothing here branches on which arm is asking.
 *
 * That is the whole reason this is a capability rather than three folders. The
 * retiring client had the institution's authoring, the partner's and the
 * platform admin's as separate trees, and a fix to one reached the others when
 * somebody remembered.
 *
 * Gated on `read_org`, which is the backend's answer for "may this person see
 * the organisation's own material at all".
 */
export const authoringCapability: CapabilityModule = {
  id: "authoring",
  title: "Authoring",
  description: "Stations, templates, rubrics, exams and programmes.",
  surfaces: ["assess", "partner", "platform"],
  permission: "read_org",
  path: "/authoring",
  icon: LuPencilRuler,
};
