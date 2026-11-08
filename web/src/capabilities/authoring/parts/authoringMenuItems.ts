import type { ActionMenuItem } from "@/foundation/ui";

/** A menu item that is a write: hidden from anyone who cannot author, as `AuthoringIconAction write` is. */
export type AuthoringMenuItem = ActionMenuItem & { write?: boolean };

/** Drops skipped entries and, for a reader, every write; the result is what `ActionMenu` takes. */
export function visibleMenuItems(items: readonly (AuthoringMenuItem | false | null | undefined)[], canAuthor: boolean): ActionMenuItem[] {
  const shown: ActionMenuItem[] = [];
  for (const item of items) {
    if (!item || (item.write && !canAuthor)) continue;
    const { write: _write, ...rest } = item;
    shown.push(rest);
  }
  return shown;
}
