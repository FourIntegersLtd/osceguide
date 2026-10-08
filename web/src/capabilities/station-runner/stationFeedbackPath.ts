/** A station's feedback for one attempt, read on its own page. Library practice and an organisation's self practice share it. */
export function stationFeedbackPath(stationId: string, attemptId: string): string {
  return `/stations/${stationId}/practise?action=review&tab=feedback&attempt=${attemptId}`;
}
