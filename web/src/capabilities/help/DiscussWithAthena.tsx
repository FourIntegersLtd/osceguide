"use client";

import { AthenaAvatar, Button } from "@/foundation/ui";
import { openAthena, type AthenaTopic } from "@/capabilities/help/api";

/**
 * Starts a spoken conversation with Athena about one subject.
 *
 * Sits beside something a person is reading, or under an answer in the typed
 * knowledge chat. It opens the dock and starts the call on that subject, so
 * she greets them with it and looks it up in the material before she explains
 * anything. The dock lives in the shell; this only asks it to open.
 */
export function DiscussWithAthena({ topic, className }: { topic: AthenaTopic; className?: string }) {
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      className={["shrink-0 gap-2", className].filter(Boolean).join(" ")}
      onClick={() => openAthena("athena", topic)}
    >
      <AthenaAvatar className="h-5 w-5" />
      <span>Discuss with Athena</span>
    </Button>
  );
}
