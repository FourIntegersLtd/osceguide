"use client";

import type { ReactNode } from "react";
import { Badge } from "@/foundation/ui";
import { statusTone } from "@/domains/platform/support";

/**
 * An organisation's status, coloured by whether its members can sign in.
 *
 * `trial` is amber rather than green on purpose: it permits access and it is
 * also the state somebody is meant to act on before it lapses.
 */
export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={statusTone(status)}>{status || "active"}</Badge>;
}

/**
 * A field the backend takes and does not give back.
 *
 * Used on the contract dates. Writing a value you cannot read back is worth
 * saying out loud on the screen rather than leaving an administrator to wonder
 * whether the save worked.
 */
export function WriteOnlyNote({ children }: { children: ReactNode }) {
  return <p className="text-osce-meta text-b2c-text-muted">{children}</p>;
}
