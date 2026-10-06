/** The stations list keeps its status filter and the open station in the address. */

export type StationStatusFilter = "active" | "archived" | "all";

export const STATION_STATUS_FILTERS: { value: StationStatusFilter; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "archived", label: "Archived" },
  { value: "all", label: "All" },
];

/** An unknown or missing value is the default, so a hand-edited address never breaks the list. */
export function parseStatusFilter(value: string | null): StationStatusFilter {
  return value === "archived" || value === "all" ? value : "active";
}

/** The list's address for a filter and, optionally, an open station; "active" is the default and is left out. */
export function stationListUrl(
  listPath: string,
  state: { status: StationStatusFilter; station?: string | null },
): string {
  const params = new URLSearchParams();
  if (state.status !== "active") params.set("status", state.status);
  if (state.station) params.set("station", state.station);
  const query = params.toString();
  return query ? `${listPath}?${query}` : listPath;
}

/** Whether the server's answer (which holds active and archived together) belongs under the filter. */
export function matchesStatusFilter(status: string, filter: StationStatusFilter): boolean {
  if (filter === "all") return true;
  return filter === "archived" ? status === "archived" : status !== "archived";
}
