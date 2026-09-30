/**
 * Marking the parts of the page the agent should not see.
 *
 * html2canvas rasterises whatever is on screen, which includes Athena's own
 * panel and the progress card raised while she works. Leaving them in costs
 * vision tokens on her own transcript and lets her point at her own UI, so both
 * carry this attribute and are dropped before the capture.
 */
export const UI_GUIDANCE_IGNORE_ATTRIBUTE = "data-ui-guidance-ignore";

/** Spread onto any element that should be invisible to screen capture. */
export const uiGuidanceIgnoreProps = {
  [UI_GUIDANCE_IGNORE_ATTRIBUTE]: "true",
} as const;

/** The `ignoreElements` predicate for html2canvas. */
export function ignoreMarkedElements(element: Element): boolean {
  return element.closest(`[${UI_GUIDANCE_IGNORE_ATTRIBUTE}]`) !== null;
}
