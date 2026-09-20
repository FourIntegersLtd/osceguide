/** Station authoring flows outside the tabbed `/authoring/{section}` shell. */

export function stationsListPath(hrefFor: (path: string) => string): string {
  return `${hrefFor("/authoring")}/stations`;
}

export function stationNewPath(hrefFor: (path: string) => string): string {
  return `${stationsListPath(hrefFor)}/new`;
}
