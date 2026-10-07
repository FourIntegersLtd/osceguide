import { can, useSession } from "@/foundation/session";

/** Whether the backend lets this person write authoring content in the active workspace. */
export function useCanAuthor(): boolean {
  const { session } = useSession();
  return can(session, "author_content");
}
