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
 * Gated on `run_circuits` *or* `administer_platform`. Inside an organisation the
 * first is the backend's answer for "is this person staff" (a trainee reads
 * no authoring data). On the staff console nobody has it — OSCE Guide's own people belong to
 * no organisation — and the second is what says they may edit the platform
 * catalogue.
 */
export const authoringCapability: CapabilityModule = {
  id: "authoring",
  title: "Authoring",
  description: "Marking schemes, exams, programmes, templates and stations.",
  surfaces: ["assess", "hire", "partner", "platform"],
  permission: ["run_circuits", "administer_platform"],
  path: "/authoring",
  staffHiddenOn: ["assess", "hire"],
  icon: LuPencilRuler,
  section: "catalogue",
};
