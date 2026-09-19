/**
 * Where the library's own screens live, expressed once.
 *
 * The detail view and the consultation are query parameters on the library's
 * single route rather than route files of their own. That is not a shortcut:
 * a capability is mounted by whichever arms list it, and a nested route file
 * would have to be added under every arm that mounts one — which is exactly
 * the per-arm duplication ADR 0001 exists to prevent. The base path is always
 * the surface's, through `hrefFor`, so no prefix is ever written down here.
 */

/** The query key naming the station a detail view is about. */
export const STATION_PARAM = "station";
/** Present when the candidate is in the consultation rather than reading. */
export const PRACTISE_PARAM = "practise";

type HrefFor = (path: string) => string;

export function libraryHref(hrefFor: HrefFor): string {
  return hrefFor("/stations");
}

export function stationHref(hrefFor: HrefFor, stationId: string): string {
  return `${libraryHref(hrefFor)}?${STATION_PARAM}=${encodeURIComponent(stationId)}`;
}

export function practiseHref(hrefFor: HrefFor, stationId: string): string {
  return `${stationHref(hrefFor, stationId)}&${PRACTISE_PARAM}=1`;
}
