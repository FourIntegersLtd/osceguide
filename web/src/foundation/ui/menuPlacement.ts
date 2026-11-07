export type PanelPlace = { top: number; right: number };
type Rect = { top: number; bottom: number; right: number };

const GAP = 4;
const EDGE = 8;

/** Where a fixed menu panel goes: right edge under the trigger's right edge, flipped above when it would run off the bottom and there is room, and kept inside the viewport on every side. */
export function placePanel(trigger: Rect, panelHeight: number, viewportWidth: number, viewportHeight: number, panelWidth = 0): PanelPlace {
  const below = trigger.bottom + GAP;
  const fitsBelow = below + panelHeight <= viewportHeight - EDGE;
  const above = trigger.top - GAP - panelHeight;
  const top = fitsBelow || above < EDGE ? below : above;
  const right = Math.max(EDGE, Math.min(viewportWidth - trigger.right, viewportWidth - panelWidth - EDGE));
  return { top: Math.max(EDGE, Math.min(top, viewportHeight - panelHeight - EDGE)), right };
}
