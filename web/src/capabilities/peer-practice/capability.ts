import { LuHandshake } from "react-icons/lu";
import type { CapabilityModule } from "@/capabilities/contract";

/**
 * Practising with another person: a queue that pairs you now, and a
 * marketplace of arranged times.
 *
 * Mounted on Train today. Both halves carry an audience the backend scopes, so
 * adding `"assess"` here gives an institution a cohort-only version — which is
 * the point of it being a capability rather than a consumer feature.
 */
export const peerPracticeCapability: CapabilityModule = {
  id: "peer-practice",
  title: "Practise with someone",
  description: "Be paired with another candidate, now or at a time you arrange.",
  surfaces: ["train"],
  permission: null,
  section: "connect",
  path: "/peers",
  icon: LuHandshake,
};
