/**
 * The consultation's optional captions, kept here so they can be tested
 * without a room. The mic toggle is `micToggle` in `foundation/livekit`.
 */

export interface CaptionLine {
  id: string;
  speaker: "you" | "patient";
  text: string;
  /** LiveKit's `firstReceivedTime`, so lines stay in the order they were spoken. */
  at: number;
}

/**
 * The captions after a batch of transcription segments: a segment updates the
 * line with its id (LiveKit resends a segment as it is refined), and only the
 * last `keep` lines are shown.
 */
export function addCaptions(
  lines: readonly CaptionLine[],
  incoming: readonly CaptionLine[],
  keep = 3,
): CaptionLine[] {
  const byId = new Map(lines.map((line) => [line.id, line]));
  for (const line of incoming) {
    if (line.text.trim()) byId.set(line.id, line);
  }
  return [...byId.values()].sort((a, b) => a.at - b.at).slice(-keep);
}
