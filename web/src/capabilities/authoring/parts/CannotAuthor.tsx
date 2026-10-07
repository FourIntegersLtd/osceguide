import { Alert } from "@/foundation/ui";

/** Stands in for an editor screen when the person may read authoring content but not write it. */
export function CannotAuthor() {
  return <Alert tone="warning">Only an organisation administrator can edit this.</Alert>;
}
