"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { LibraryBrowse } from "@/capabilities/stations/LibraryBrowse";
import { StationConsultation } from "@/capabilities/stations/StationConsultation";
import { StationDetail } from "@/capabilities/stations/StationDetail";
import { StationPicker, type StationPickerProps } from "@/capabilities/stations/StationPicker";
import { PRACTISE_PARAM, STATION_PARAM } from "@/capabilities/stations/routes";

export type StationLibraryProps = Partial<StationPickerProps>;

/**
 * The station library, wherever it is mounted.
 *
 * Two shapes behind one export, because two things want it. Given `onPick` it
 * is a picker inside somebody's form — that is how a mock and a circuit are
 * built. Given nothing it is the section itself: browse, one station, and the
 * consultation, which are query parameters on the one route rather than route
 * files, so mounting the library on a fourth arm stays a line in
 * `capability.ts` and not a tree of pages per arm.
 */
export function StationLibrary(props: StationLibraryProps) {
  const { onPick, pickLabel, selectedVersionIds } = props;

  // A picker reads no query string, so it needs no boundary — and must not be
  // suspended by one, since it renders inside a form that is already open.
  if (onPick) {
    return (
      <StationPicker
        onPick={onPick}
        pickLabel={pickLabel}
        selectedVersionIds={selectedVersionIds}
      />
    );
  }

  // `useSearchParams` needs a boundary in the app router. It is here rather
  // than in the route file so that every arm mounting this capability gets it
  // without knowing it was needed.
  return (
    <Suspense fallback={null}>
      <LibraryRoute />
    </Suspense>
  );
}

function LibraryRoute() {
  const params = useSearchParams();
  const stationId = params.get(STATION_PARAM);

  if (!stationId) return <LibraryBrowse />;
  if (params.get(PRACTISE_PARAM)) return <StationConsultation stationId={stationId} />;
  return <StationDetail stationId={stationId} />;
}
