import { useEffect, useState } from "react";
import { isUiGuidanceEnabled } from "./config"; /** Match Tailwind `lg`. Pointers, overlays, and computer RPCs need a laptop-sized layout. */
export const UI_GUIDANCE_MIN_WIDTH_PX = 1024;
const mqString = `(min-width: ${UI_GUIDANCE_MIN_WIDTH_PX}px)`; /** * Screen capture, pointer overlay, scroll/click RPCs. Desktop only. * Mobile/tablet: voice-only step-by-step (no overlays or computer tool). */
export function getScreenUiGuidanceActive(): boolean {
  if (typeof window === "undefined") return false;
  if (!isUiGuidanceEnabled()) return false;
  return window.matchMedia(mqString).matches;
}
export function useScreenUiGuidance(): boolean {
  const [active, setActive] = useState(false);
  useEffect(() => {
    const update = () => setActive(getScreenUiGuidanceActive());
    update();
    const mq = window.matchMedia(mqString);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return active;
}
