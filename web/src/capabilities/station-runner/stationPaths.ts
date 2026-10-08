/** Where a library station is practised, shared by library practice and an organisation's self practice. Kept apart from `stationSource` so a node test can import it. */
const practisePath = (stationId: string) => `/stations/${stationId}/practise`;

/** Sitting a library station: starts an attempt. */
export function stationAttemptPath(stationId: string): string {
  return `${practisePath(stationId)}?action=attempt`;
}

/**
 * A station's feedback on its own review tab: one attempt's, or (no `attemptId`) the past ones.
 * Library practice and an organisation's self practice share it.
 */
export function stationFeedbackPath(stationId: string, attemptId?: string): string {
  const base = `${practisePath(stationId)}?action=review&tab=feedback`;
  return attemptId ? `${base}&attempt=${attemptId}` : base;
}

