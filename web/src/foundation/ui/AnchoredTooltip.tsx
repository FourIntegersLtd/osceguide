"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

export type AnchoredTooltipPlacement = "top" | "right" | "bottom" | "left";

type Coords = { left: number; top: number; transform: string };

const GAP = 8;

function coordsFor(rect: DOMRect, placement: AnchoredTooltipPlacement): Coords {
  switch (placement) {
    case "left":
      return {
        left: rect.left - GAP,
        top: rect.top + rect.height / 2,
        transform: "translate(-100%, -50%)",
      };
    case "top":
      return {
        left: rect.left + rect.width / 2,
        top: rect.top - GAP,
        transform: "translate(-50%, -100%)",
      };
    case "bottom":
      return {
        left: rect.left + rect.width / 2,
        top: rect.bottom + GAP,
        transform: "translate(-50%, 0)",
      };
    case "right":
    default:
      return {
        left: rect.right + GAP,
        top: rect.top + rect.height / 2,
        transform: "translate(0, -50%)",
      };
  }
}

type Props = {
  label: string;
  placement?: AnchoredTooltipPlacement;
  /** Visual styling for the tooltip chip (colour, radius, type scale). */
  chipClassName: string;
  /** Classes for the inline wrapper around the trigger. */
  className?: string;
  /** Optional extra node rendered inside the chip (e.g. a pointer arrow). */
  chipDecoration?: ReactNode;
  children: ReactNode;
};

/**
 * Hover/focus tooltip rendered in a portal with fixed positioning, so it stays
 * visible when the trigger sits inside a scrolling or clipping container (e.g.
 * the collapsed sidebar's `overflow-y-auto` icon list).
 */
export function AnchoredTooltip({
  label,
  placement = "bottom",
  chipClassName,
  className = "",
  chipDecoration,
  children,
}: Props) {
  const anchorRef = useRef<HTMLSpanElement | null>(null);
  const [coords, setCoords] = useState<Coords | null>(null);

  const show = useCallback(() => {
    const node = anchorRef.current;
    if (!node) return;
    setCoords(coordsFor(node.getBoundingClientRect(), placement));
  }, [placement]);

  const hide = useCallback(() => setCoords(null), []);

  useEffect(() => {
    if (!coords) return;
    const reposition = () => show();
    window.addEventListener("scroll", reposition, true);
    window.addEventListener("resize", reposition);
    return () => {
      window.removeEventListener("scroll", reposition, true);
      window.removeEventListener("resize", reposition);
    };
  }, [coords, show]);

  return (
    <span
      ref={anchorRef}
      className={["inline-flex", className].filter(Boolean).join(" ")}
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      {coords && typeof document !== "undefined"
        ? createPortal(
            <span
              role="tooltip"
              className={chipClassName}
              style={{
                position: "fixed",
                left: coords.left,
                top: coords.top,
                transform: coords.transform,
              }}
            >
              {label}
              {chipDecoration}
            </span>,
            document.body,
          )
        : null}
    </span>
  );
}
