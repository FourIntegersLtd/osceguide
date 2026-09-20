import type { LocalParticipant } from "livekit-client";
import {
  performScrollRpcRequestSchema,
  performScrollRpcResponseSchema,
  RPC_METHOD_SCROLL,
} from "./contracts";
const DEFAULT_AMOUNT_PX = 420;
function tryScrollFromElement(
  startEl: Element | null,
  dx: number,
  dy: number,
): boolean {
  let node: HTMLElement | null =
    startEl instanceof HTMLElement ? startEl : null;
  while (node) {
    const st = window.getComputedStyle(node);
    const oy = st.overflowY;
    const ox = st.overflowX;
    const canY =
      (oy === "auto" || oy === "scroll" || oy === "overlay") &&
      node.scrollHeight > node.clientHeight + 1;
    const canX =
      (ox === "auto" || ox === "scroll" || ox === "overlay") &&
      node.scrollWidth > node.clientWidth + 1;
    if (canY && dy !== 0) {
      const before = node.scrollTop;
      node.scrollTop += dy;
      if (Math.abs(node.scrollTop - before) > 0.5) return true;
    }
    if (canX && dx !== 0) {
      const before = node.scrollLeft;
      node.scrollLeft += dx;
      if (Math.abs(node.scrollLeft - before) > 0.5) return true;
    }
    node = node.parentElement;
  }
  return false;
} /** * Registers LiveKit RPC `performUiGuidanceScroll`. Scrolls the main window and/or * nested overflow containers (e.g. App layout with overflow-y-auto). */
export function registerScrollRpc(localParticipant: LocalParticipant): void {
  localParticipant.registerRpcMethod(
    RPC_METHOD_SCROLL,
    async (rpcInvocation) => {
      const parsed = performScrollRpcRequestSchema.parse(
        JSON.parse(rpcInvocation.payload || "{}"),
      );
      const { direction } = parsed;
      const amountPx =
        typeof parsed.amount_px === "number" &&
        Number.isFinite(parsed.amount_px)
          ? Math.min(2000, Math.max(40, Math.round(parsed.amount_px)))
          : DEFAULT_AMOUNT_PX;
      const dx =
        direction === "left" ? -amountPx : direction === "right" ? amountPx : 0;
      const dy =
        direction === "up" ? -amountPx : direction === "down" ? amountPx : 0;
      try {
        const beforeX = window.scrollX;
        const beforeY = window.scrollY;
        window.scrollBy({ left: dx, top: dy, behavior: "auto" });
        const root = document.scrollingElement;
        if (root) {
          root.scrollBy({ left: dx, top: dy, behavior: "auto" });
        }
        let moved =
          Math.abs(window.scrollX - beforeX) > 0.5 ||
          Math.abs(window.scrollY - beforeY) > 0.5;
        if (!moved && (dx !== 0 || dy !== 0)) {
          const cx = window.innerWidth / 2;
          const cy = window.innerHeight / 2;
          const stack = document.elementsFromPoint(cx, cy);
          for (const el of stack) {
            if (tryScrollFromElement(el, dx, dy)) {
              moved = true;
              break;
            }
          }
        }
        await new Promise<void>((r) => {
          requestAnimationFrame(() => requestAnimationFrame(() => r()));
        });
        await new Promise((r) => setTimeout(r, 120));
        return JSON.stringify(
          performScrollRpcResponseSchema.parse({
            ok: true,
            moved,
            scroll_x: window.scrollX,
            scroll_y: window.scrollY,
          }),
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return JSON.stringify(
          performScrollRpcResponseSchema.parse({ ok: false, error: message }),
        );
      }
    },
  );
}
