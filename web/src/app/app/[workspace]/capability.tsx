"use client";

import type { ReactNode } from "react";
import { notFound } from "next/navigation";
import { useCapabilityGate } from "@/surfaces/useCapabilityGate";

/**
 * A capability's page, on whichever arm is asking.
 *
 * The component inside is the same everywhere — that is what makes it a
 * capability — but not every arm mounts every one. This is the gate: a
 * capability that does not list this arm, or whose permission the backend has
 * not granted, is a 404 (or its `unmountedGoesTo`) rather than a section that
 * quietly appears for somebody who cannot use it.
 */
export function Capability({ id, children }: { id: string; children: ReactNode }) {
  const gate = useCapabilityGate(id);
  if (gate === "loading" || gate === "bounce") return null;
  if (gate === "missing") notFound();
  return <>{children}</>;
}
