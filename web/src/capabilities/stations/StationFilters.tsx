"use client";

import { LuSearch } from "react-icons/lu";
import { cn } from "@/foundation/ui";
import { b2cInputBase } from "@/foundation/ui/productTokens";
import type { StationLibraryState } from "@/capabilities/stations/useStationLibrary";

/**
 * The one way into a library of a few hundred scenarios: a word from the title.
 *
 * There used to be an exam filter here too — an "All exams" chip and one per
 * published exam. It is gone because it was answering a question nobody asked:
 * the retiring client had one exam per deployment and no such control, almost
 * nobody holds two exams, and the chips were drawn from the whole catalogue
 * rather than from what the person had bought. The exam is the app's now, set
 * once in the navigation, and `GET /api/v1/stations` refuses any other.
 */
export function StationFilters({ library }: { library: StationLibraryState }) {
  return (
    <label className="relative block">
      <span className="sr-only">Search stations by name</span>
      <LuSearch
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-b2c-text-muted"
        aria-hidden
      />
      <input
        type="search"
        value={library.search}
        onChange={(event) => library.setSearch(event.target.value)}
        placeholder="Search stations by name..."
        className={cn(b2cInputBase, "pl-9")}
      />
    </label>
  );
}
