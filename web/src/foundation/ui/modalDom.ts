/** DOM helpers for the B2C Modal shell (React-free). */

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function getFocusable(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.offsetParent !== null || el === document.activeElement,
  );
}

export function resolveModalWidth(
  width?: string | { mobile: string; desktop: string },
): string {
  if (!width) return "100%";
  if (typeof width === "object") {
    return `clamp(${width.mobile}, 100%, ${width.desktop})`;
  }
  if (/^w-/.test(width)) {
    return width === "w-1/2" ? "50%" : "100%";
  }
  return width;
}

export function isFitContentHeight(height?: string): boolean {
  return !height || height === "auto" || height === "fit-content";
}

export function lockAppScroll(): () => void {
  const body = document.body;
  const scrollMain = document.querySelector<HTMLElement>("main[data-b2c-scroll]");
  const previousBodyOverflow = body.style.overflow;
  const previousMainOverflow = scrollMain?.style.overflow ?? "";

  body.style.overflow = "hidden";
  if (scrollMain) scrollMain.style.overflow = "hidden";

  return () => {
    body.style.overflow = previousBodyOverflow;
    if (scrollMain) scrollMain.style.overflow = previousMainOverflow;
  };
}
