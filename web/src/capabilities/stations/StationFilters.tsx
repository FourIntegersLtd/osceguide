"use client";

import type { StationLibraryState } from "@/capabilities/stations/useStationLibrary";
import { SectionSearchField } from "@/foundation/ui";

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
    <SectionSearchField
      value={library.search}
      onChange={library.setSearch}
      placeholder="Search stations by name..."
      ariaLabel="Search stations by name"
      maxWidthClass="max-w-md"
    />
  );
}
