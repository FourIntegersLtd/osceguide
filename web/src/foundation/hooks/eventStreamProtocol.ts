/** Resolve same-origin API proxies as well as absolute API origins. */
export function streamUrl(base: string, path: string, origin: string, ticket: string): string {
  const url = new URL(`${base}${path}`, origin);
  url.searchParams.set("ticket", ticket);
  return url.toString();
}

/** Platform streams use named snapshot events; connected/ping are not data. */
export function listenForSnapshots<T>(source: EventTarget, onData: (data: T) => void): () => void {
  const receive = (event: Event) => {
    if (!(event instanceof MessageEvent)) return;
    let value: T;
    try { value = JSON.parse(event.data) as T; }
    catch { return; }
    onData(value);
  };
  source.addEventListener("snapshot", receive);
  source.addEventListener("message", receive);
  return () => {
    source.removeEventListener("snapshot", receive);
    source.removeEventListener("message", receive);
  };
}
