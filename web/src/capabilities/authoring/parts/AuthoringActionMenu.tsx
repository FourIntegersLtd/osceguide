"use client";

import { ActionMenu } from "@/foundation/ui";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";
import { visibleMenuItems, type AuthoringMenuItem } from "@/capabilities/authoring/parts/authoringMenuItems";

/** The "⋯" menu of a row or header: `write` items are hidden from anyone who cannot author, and an empty menu draws nothing. */
export function AuthoringActionMenu({ items, label }: { items: readonly (AuthoringMenuItem | false | null | undefined)[]; label?: string }) {
  const canAuthor = useCanAuthor();
  const shown = visibleMenuItems(items, canAuthor);
  return shown.length === 0 ? null : <ActionMenu items={shown} label={label} />;
}
