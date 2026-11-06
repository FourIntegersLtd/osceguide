import type { BoardChipTone } from "@/foundation/ui/boardKit";

/** Status text to a chip tone and the board's wording ("● Published"). */
export function statusChip(status: string | undefined): { tone: BoardChipTone; label: string } {
  switch (status) {
    case "published":
      return { tone: "ok", label: "● Published" };
    case "active":
      return { tone: "ok", label: "● Active" };
    case "retired":
      return { tone: "neutral", label: "● Retired" };
    case "archived":
      return { tone: "neutral", label: "● Archived" };
    default:
      return { tone: "warn", label: "● Draft" };
  }
}
