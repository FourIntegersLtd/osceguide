import { PEER_JOIN_EARLY_MINUTES } from "@/capabilities/peer-practice/limits";
import type { Slot } from "@/capabilities/peer-practice/api";

/** The marketplace's wording, kept as plain values so it can be pinned by tests. */

export function introTitle(examName: string | null): string {
  return examName ? `Practise the ${examName} with a colleague` : "Practise with a colleague";
}

export const INTRO_DESCRIPTION =
  "Practise the SCA over video with a colleague. Post when you're free, or book someone else's slot.";

export const HOW_IT_WORKS_DESCRIPTION = "Practise with a colleague over video. Here is how a session works.";

export const HOW_IT_WORKS_STEPS = [
  {
    title: "Post when you're free",
    text: "Pick a date and time, and add a note if you like.",
  },
  {
    title: "Someone books your slot",
    text: "When a colleague books it, you both get a confirmed video session.",
  },
  {
    title: "Join the video call",
    text: `Join the video call up to ${PEER_JOIN_EARLY_MINUTES} minutes before it starts. We'll tell you whether you're the doctor or the patient.`,
  },
  {
    title: "Practise together",
    text: "You both get reading time, then the consultation begins. The timers start once you've both joined.",
  },
] as const;

export type SlotBadge = "Available" | "Scheduled" | "Completed" | "Cancelled" | "Expired";

/** Exhaustive over the generated status union: a new api status fails the type check here. */
export function slotBadge(slot: Pick<Slot, "status">, past: boolean): SlotBadge {
  switch (slot.status) {
    case "cancelled":
      return "Cancelled";
    case "claimed":
      return past ? "Completed" : "Scheduled";
    case "available":
      return past ? "Expired" : "Available";
    default: {
      const unreachable: never = slot.status;
      return unreachable;
    }
  }
}

/** The line under a slot nobody has booked; your own slot speaks in the first person. */
export function openSlotLine(slot: Pick<Slot, "status" | "is_mine">, past: boolean): string {
  if (slot.status === "cancelled") return slot.is_mine ? "You cancelled this slot" : "This slot was cancelled";
  if (past) return "Nobody booked this slot";
  return slot.is_mine ? "You're looking for a partner" : "is looking for a practice partner";
}
