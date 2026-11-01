/**
 * The empty-library sentence the four study libraries share. With an exam picked, an empty list
 * means that exam has nothing open to this person; without one, each library keeps its own line.
 */
export function emptyLibraryDescription(examCode: string | null | undefined, noExamCopy: string): string {
  return examCode ? `Nothing published for ${examCode.toUpperCase()} yet. Upgrade for full access.` : noExamCopy;
}

export const NO_SLIDES_COPY = "Check back later for new content.";
export const NO_EPISODES_COPY = "Episodes appear here as they are published.";
