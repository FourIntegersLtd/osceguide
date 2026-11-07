"use client";

import { assessMeta } from "@/foundation/ui/b2bTokens";
import { RailSection } from "@/domains/assess/sessions/RailSection";

/** The ended circuit's "Transcripts and AI marks" note, in the rail. The stations list is the one above. */
export function CircuitRecordNote() {
  return (
    <RailSection id="record" title="Transcripts and AI marks">
      <p className={assessMeta}>
        Open a station to read what was said. Only the supervisor on this circuit can see it.
      </p>
    </RailSection>
  );
}
