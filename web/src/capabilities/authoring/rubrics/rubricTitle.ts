/**
 * Pure decisions for the rubric builder's inline rename control (R-7).
 *
 * Kept out of `RubricBuilderScreen.tsx` so they can be unit-tested directly:
 * a `.tsx` file cannot be imported by a plain node test (`AGENTS.md`, "Traps
 * a browser run has hit").
 */

/**
 * What a rename submit should send, or `null` when nothing should be sent.
 *
 * Trims the typed value first, since a title of only spaces means the same
 * as leaving it blank (the backend's `RenameRubric.title_is_visible` refuses
 * it too, but this is what stops the browser round-tripping an unwanted or
 * unchanged request). Returns `null` when the trimmed value is empty or is
 * exactly the rubric's current title.
 */
export function nextRubricTitle(currentTitle: string, typed: string): string | null {
  const trimmed = typed.trim();
  if (!trimmed || trimmed === currentTitle) {
    return null;
  }
  return trimmed;
}
