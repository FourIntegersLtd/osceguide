export function splitMultilineToTrimmedLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
} /** * Same as splitting on newlines and trimming each line, but keeps empty lines so multiline * editors still show blank rows while the user types (Enter after "Item 1" Must stay visible). */
export function splitMultilineToTrimmedLinesKeepEmpty(value: string): string[] {
  return value.split("\n").map((line) => line.trim());
}
