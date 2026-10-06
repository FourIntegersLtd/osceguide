/**
 * The new name to save, or undefined when the typed one is the saved one.
 *
 * Both sides are trimmed: a saved title can carry a stray space (an import wrote some), and typing
 * it back as it was must not make the draft look edited.
 */
export function renamedTitle(typed: string, saved: string): string | undefined {
  const next = typed.trim();
  return next !== saved.trim() ? next : undefined;
}
