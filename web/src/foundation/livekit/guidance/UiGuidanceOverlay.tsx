"use client";
import { createPortal } from "react-dom";
import { useEffect, useRef, useState } from "react";
import type { UiGuidancePointer } from "./useUiGuidance";
import { b2cTokens } from "./tokens";
type Props = {
  /** When set, draws the highlight at these viewport coordinates. */ pointerTarget: UiGuidancePointer | null;
  zIndex?: number;
};
const GLIDE_DURATION_MS = 600;
const CURSOR_SIZE = 28;
/** The SVG tip is at the top-left corner. offset so the tip lands on the target. */
const CURSOR_TIP_OFFSET = { x: 2, y: 1 };
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}
export function UiGuidanceOverlay({
  pointerTarget,
  zIndex = 2147483000,
}: Props) {
  const [pos, setPos] = useState({ x: -999, y: -999 });
  const [arrived, setArrived] = useState(false);
  const [visible, setVisible] = useState(false);
  const lastPosRef = useRef({ x: -999, y: -999 });
  const rafRef = useRef<number | null>(null);
  useEffect(() => {
    if (!pointerTarget) {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      setVisible(false);
      setArrived(false);
      return;
    }
    const target = { x: pointerTarget.x, y: pointerTarget.y };
    const start = { ...lastPosRef.current };
    const isFirstAppearance = start.x === -999 && start.y === -999;
    const t0 = performance.now();
    if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    setArrived(false);
    setVisible(true);
    if (isFirstAppearance) {
      lastPosRef.current = target;
      setPos(target);
      setArrived(true);
      return;
    }
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / GLIDE_DURATION_MS);
      const e = easeOutCubic(p);
      const x = start.x + (target.x - start.x) * e;
      const y = start.y + (target.y - start.y) * e;
      lastPosRef.current = { x, y };
      setPos({ x, y });
      if (p < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        rafRef.current = null;
        lastPosRef.current = target;
        setPos(target);
        setArrived(true);
      }
    };
    rafRef.current = requestAnimationFrame(step);
    return () => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
    };
  }, [pointerTarget?.x, pointerTarget?.y, pointerTarget?.text, pointerTarget]);
  if (typeof document === "undefined" || !pointerTarget || !visible)
    return null;
  const cursorLeft = pos.x - CURSOR_TIP_OFFSET.x;
  const cursorTop = pos.y - CURSOR_TIP_OFFSET.y;
  return createPortal(
    <div
      className="pointer-events-none fixed inset-0"
      style={{ zIndex }}
      aria-hidden="true"
    >
      {" "}
      {/* ── Pulsing ring at target (visible once cursor arrives) ── */}{" "}
      {arrived && (
        <div
          style={{
            position: "absolute",
            left: pos.x,
            top: pos.y,
            transform: "translate(-50%, -50%)",
          }}
        >
          {" "}
          <div
            className="ui-guidance-ring"
            style={{
              width: 36,
              height: 36,
              borderRadius: "50%",
              border: "2.5px solid #2563eb",
              background: "rgba(59, 130, 246, 0.08)",
            }}
          />{" "}
        </div>
      )}{" "}
      {/* ── Animated pointer cursor ── */}{" "}
      <svg
        width={CURSOR_SIZE}
        height={CURSOR_SIZE}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{
          position: "absolute",
          left: cursorLeft,
          top: cursorTop,
          filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.25))",
          transition: arrived ? "none" : undefined,
        }}
      >
        {" "}
        {/* Classic pointer cursor shape */}{" "}
        <path
          d="M5.5 2L5.5 19.5L10.3 15.2L14.5 22L17.5 20.5L13.3 13.7L19.5 13L5.5 2Z"
          fill={b2cTokens.primary}
          stroke="#ffffff"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />{" "}
      </svg>{" "}
      {/* ── Label (if the agent provided one) ── */}{" "}
      {arrived && pointerTarget.text && (
        <div
          style={{
            position: "absolute",
            left: pos.x,
            top: pos.y + 26,
            transform: "translateX(-50%)",
            background: "#1e3a5f",
            color: "#ffffff",
            fontSize: 12,
            fontWeight: 600,
            fontFamily: "system-ui, sans-serif",
            padding: "3px 10px",
            borderRadius: 6,
            whiteSpace: "nowrap",
            opacity: 0.92,
          }}
        >
          {" "}
          {pointerTarget.text}{" "}
        </div>
      )}{" "}
      <style>{` .ui-guidance-ring { animation: ui-guidance-ring-pulse 1.8s ease-in-out infinite; } @keyframes ui-guidance-ring-pulse { 0%, 100% { transform: scale(1); opacity: 1; box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.3); } 50% { transform: scale(1.3); opacity: 0.7; box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); } } `}</style>{" "}
    </div>,
    document.body,
  );
}
