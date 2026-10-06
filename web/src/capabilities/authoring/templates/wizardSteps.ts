import type { RailStep } from "@/foundation/ui";

export type WizardStepId = "start" | "sections";

/** The template wizard's two screens: exam, name and layout, then sections and fields. */
export function wizardSteps(current: WizardStepId, started: boolean): RailStep<WizardStepId>[] {
  return [
    {
      id: "start",
      label: "Start",
      state: current === "sections" ? "done" : "todo",
      note: started ? "Exam, name, layout" : "Choose exam and layout",
    },
    {
      id: "sections",
      label: "Sections & fields",
      state: "todo",
      note: "Then save a draft",
    },
  ];
}
