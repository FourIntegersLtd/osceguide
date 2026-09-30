"use client";

import { Button, SectionSearchField } from "@/foundation/ui";
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
 *
 * The term is submitted — Enter, or the button that appears once something is
 * typed — because the search is a request now rather than a filter over what
 * the browser happens to hold. That is the retiring list's own shape: its table
 * searched on submit and cleared the filter the moment the box was emptied.
 */
export function StationFilters({ library }: { library: StationLibraryState }) {
  const typed = library.search.trim() !== "";

  return (
    <SectionSearchField
      value={library.search}
      onChange={library.setSearch}
      onSubmit={library.applySearch}
      placeholder="Search stations by name..."
      ariaLabel="Search stations by name"
      maxWidthClass="max-w-md"
      trailing={
        typed ? (
          <>
            <Button type="button" variant="secondary" size="sm" onClick={library.clearSearch}>
              Clear
            </Button>
            <Button type="submit" size="sm">
              Search
            </Button>
          </>
        ) : null
      }
    />
  );
}
