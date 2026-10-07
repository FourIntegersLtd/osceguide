"use client";

import type { ReactNode } from "react";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { CannotAuthor } from "@/capabilities/authoring/parts/CannotAuthor";

/** Renders an editor screen for an author, and the refusal for anyone else. */
export function RequireAuthor({ children }: { children: ReactNode }) {
  return useCanAuthor() ? children : <CannotAuthor />;
}
