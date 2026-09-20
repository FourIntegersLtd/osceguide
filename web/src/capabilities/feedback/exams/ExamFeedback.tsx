import type { ComponentProps } from "react";
import PlabFeedback from "./PlabFeedback";
import CascFeedback from "./CascFeedback";
import OrthoFeedback from "./OrthoFeedback";

import { feedbackExam } from "./examPayload";
export { feedbackExam } from "./examPayload";
type RecordValue = Record<string, unknown>;

/** Validate the engine payload before entering the original exam-specific views. */
export function ExamFeedback({ payload }: { payload: RecordValue }) {
  switch (feedbackExam(payload)) {
    case "plab":
      return <PlabFeedback feedback={payload as unknown as ComponentProps<typeof PlabFeedback>["feedback"]} />;
    case "casc":
      return <CascFeedback feedback={payload as unknown as ComponentProps<typeof CascFeedback>["feedback"]} />;
    case "ortho":
      return <OrthoFeedback feedback={payload as unknown as ComponentProps<typeof OrthoFeedback>["feedback"]} />;
    default:
      return null;
  }
}
