import type { OrgStation } from "@/domains/assess/trainee/api";

/**
 * The station a self-practice link names, only if it can be sat.
 *
 * A link can name a station that is gone, still a draft, or another organisation's (the list
 * only holds this organisation's own); each of those used to leave a blank page. Practising
 * needs a published version to bind to.
 */
export function practisableStation(stations: readonly OrgStation[], stationId: string): OrgStation | null {
  const station = stations.find((row) => row.id === stationId);
  if (!station || station.status !== "published" || !station.current_version_id) return null;
  return station;
}
