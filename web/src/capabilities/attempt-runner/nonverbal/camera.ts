/** Stop every track of a camera stream and take the analysis video out of the page. */
export function releaseCamera(stream: MediaStream | null, video: HTMLVideoElement | null): void {
  stream?.getTracks().forEach((track) => track.stop());
  video?.remove();
}

/**
 * Await a camera request; if the caller gave up while it was pending (effect cleanup, a
 * StrictMode double mount), stop the stream that arrived late and return null.
 */
export async function acquireCamera(request: () => Promise<MediaStream>, isCancelled: () => boolean): Promise<MediaStream | null> {
  const stream = await request();
  if (isCancelled()) {
    releaseCamera(stream, null);
    return null;
  }
  return stream;
}
