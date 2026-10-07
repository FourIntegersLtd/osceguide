import { Alert } from "@/foundation/ui";

/** What a reader sees where an author would see guidance for writing. */
export const READER_EMPTY_TEXT = "Nothing here yet.";

/** Stands in for an editor screen when the person may read authoring content but not write it. */
export function CannotAuthor() {
  return <Alert tone="warning">Only an organisation administrator can edit this.</Alert>;
}
