import type { SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";

export const SCHEME_TABS: readonly { id: SchemeTabId; label: string }[] = [
  { id: "domains", label: "Domains" },
  { id: "scale", label: "Scale" },
  { id: "pass", label: "Pass rule" },
  { id: "feedback", label: "Feedback" },
  { id: "advanced", label: "Advanced" },
  { id: "trial", label: "Trial mark" },
  { id: "versions", label: "Versions" },
];

/** The tabs that edit one block of the scheme; none of them can show a scheme the builder cannot read. */
export const CONTENT_TABS: readonly SchemeTabId[] = ["scale", "pass", "feedback"];

/** The first six tabs are the steps an author walks; Versions sits beside them. */
const STEPS = SCHEME_TABS.slice(0, 6);

/** The tab a `?tab=` value names; anything else is the first tab. */
export function parseTab(value: string | null | undefined): SchemeTabId {
  return SCHEME_TABS.find((tab) => tab.id === value)?.id ?? "domains";
}

export interface TabFooter {
  step: number;
  of: number;
  /** "Step 2 of 6: Scale"; Versions reads "Versions is outside the steps". */
  where: string;
  label: string;
  back: SchemeTabId | null;
  next: SchemeTabId | null;
  backLabel: string;
  /** The last step offers Publish rather than a next tab. */
  nextLabel: string;
}

/** The footer of a tab: Back and Next name the tab they go to; Versions steps back to Domains. */
export function tabFooter(tab: SchemeTabId): TabFooter {
  const at = STEPS.findIndex((t) => t.id === tab);
  if (at < 0) return { step: 0, of: STEPS.length, where: "Versions is outside the steps", label: "Versions", back: "domains", next: null, backLabel: `Back to the steps: ${STEPS[0]!.label}`, nextLabel: "" };
  const back = STEPS[at - 1];
  const next = STEPS[at + 1];
  return {
    step: at + 1,
    of: STEPS.length,
    where: `Step ${at + 1} of ${STEPS.length}: ${STEPS[at]!.label}`,
    label: STEPS[at]!.label,
    back: back?.id ?? null,
    next: next?.id ?? null,
    backLabel: back ? `Back: ${back.label}` : "Back",
    nextLabel: next ? `Next: ${next.label}` : "Publish",
  };
}
