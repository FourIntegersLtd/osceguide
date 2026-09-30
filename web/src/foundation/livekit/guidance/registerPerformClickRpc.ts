import type { LocalParticipant } from "livekit-client";
import {
  performClickRpcRequestSchema,
  performClickRpcResponseSchema,
  RPC_METHOD_PERFORM_CLICK,
} from "./contracts"; /** * Registers LiveKit RPC `performUiGuidanceClick` On the local participant. * Agent sends viewport CSS coordinates (same space as pointer overlay). */
export function registerPerformClickRpc(
  localParticipant: LocalParticipant,
): void {
  localParticipant.registerRpcMethod(
    RPC_METHOD_PERFORM_CLICK,
    async (rpcInvocation) => {
      const { x, y } = performClickRpcRequestSchema.parse(
        JSON.parse(rpcInvocation.payload || "{}"),
      );
      try {
        const el = document.elementFromPoint(x, y);
        if (!el) {
          return JSON.stringify(
            performClickRpcResponseSchema.parse({
              ok: false,
              error: "no_element_at_point",
            }),
          );
        }
        let target: HTMLElement | null = null;
        let node: Element | null = el;
        while (node && node !== document.documentElement) {
          if (node instanceof HTMLElement) {
            const tag = node.tagName.toLowerCase();
            const role = node.getAttribute("role");
            if (
              tag === "button" ||
              tag === "a" ||
              tag === "summary" ||
              role === "button" ||
              role === "link" ||
              role === "tab" ||
              node.hasAttribute("onclick") ||
              window.getComputedStyle(node).cursor === "pointer"
            ) {
              target = node;
              break;
            }
          }
          node = node.parentElement;
        }
        if (!target) {
          target = el instanceof HTMLElement ? el : null;
        }
        if (!target) {
          return JSON.stringify(
            performClickRpcResponseSchema.parse({
              ok: false,
              error: "no_html_element",
            }),
          );
        }
        target.scrollIntoView({ block: "nearest", inline: "nearest" });
        const rect = target.getBoundingClientRect();
        const cx = Math.min(Math.max(x, rect.left + 1), rect.right - 1);
        const cy = Math.min(Math.max(y, rect.top + 1), rect.bottom - 1);
        const common = {
          bubbles: true,
          cancelable: true,
          clientX: cx,
          clientY: cy,
          view: window,
        } as const;
        target.dispatchEvent(
          new PointerEvent("pointerdown", {
            ...common,
            pointerId: 1,
            pointerType: "mouse",
          }),
        );
        target.dispatchEvent(new MouseEvent("mousedown", common));
        target.dispatchEvent(new MouseEvent("mouseup", common));
        target.dispatchEvent(new MouseEvent("click", common));
        target.dispatchEvent(
          new PointerEvent("pointerup", {
            ...common,
            pointerId: 1,
            pointerType: "mouse",
          }),
        );
        await new Promise<void>((r) => {
          requestAnimationFrame(() => requestAnimationFrame(() => r()));
        });
        await new Promise((r) => setTimeout(r, 380));
        return JSON.stringify(
          performClickRpcResponseSchema.parse({
            ok: true,
            pathname:
              typeof window !== "undefined"
                ? window.location.pathname
                : undefined,
          }),
        );
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        return JSON.stringify(
          performClickRpcResponseSchema.parse({ ok: false, error: message }),
        );
      }
    },
  );
}
