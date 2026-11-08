"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { useDismissOnOutside } from "@/foundation/hooks/useDismissOnOutside";
import { menuFocusTarget } from "@/foundation/ui/popupMenuKeys";
import { placePanel, type PanelPlace } from "@/foundation/ui/menuPlacement";
import { cn } from "@/foundation/ui/cn";

/**
 * A button that opens a menu of `role="menuitem"` buttons. Focus moves into the menu, the arrow keys, Home and End
 * move through its enabled items, Escape closes it and returns focus to the button, and a press outside closes it.
 * The button is whatever `trigger` renders; it must carry `aria-haspopup` so focus can go back to it.
 */
export function PopupMenu({
  trigger,
  children,
  className,
  fixed = false,
}: {
  trigger: (state: { open: boolean; toggle: () => void }) => ReactNode;
  children: (close: () => void) => ReactNode;
  className?: string;
  /** Position the panel with `position: fixed` from the trigger's rect, so a table or card with `overflow` cannot clip it. Closes on scroll and resize. */
  fixed?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const menu = useRef<HTMLUListElement>(null);
  const dismiss = useCallback(() => setOpen(false), []);
  useDismissOnOutside(root, open, dismiss);

  const [place, setPlace] = useState<PanelPlace | null>(null);
  useLayoutEffect(() => {
    if (!open || !fixed || !root.current || !menu.current) return setPlace(null);
    setPlace(placePanel(root.current.getBoundingClientRect(), menu.current.offsetHeight, window.innerWidth, window.innerHeight, menu.current.offsetWidth));
  }, [open, fixed]);
  useEffect(() => {
    if (!open || !fixed) return;
    window.addEventListener("scroll", dismiss, true);
    window.addEventListener("resize", dismiss);
    return () => {
      window.removeEventListener("scroll", dismiss, true);
      window.removeEventListener("resize", dismiss);
    };
  }, [open, fixed, dismiss]);

  const items = () => Array.from(menu.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not(:disabled)') ?? []);
  const closeToTrigger = useCallback(() => {
    setOpen(false);
    root.current?.querySelector<HTMLElement>("[aria-haspopup]")?.focus();
  }, []);
  // Opening moves focus to the first enabled item.
  useEffect(() => {
    if (open) menu.current?.querySelector<HTMLElement>('[role="menuitem"]:not(:disabled)')?.focus();
  }, [open]);
  const toggle = () => setOpen((v) => !v);
  const onKeyDown = (event: KeyboardEvent<HTMLUListElement>) => {
    if (event.key === "Escape") {
      event.stopPropagation();
      return closeToTrigger();
    }
    const all = items();
    const to = menuFocusTarget(all.map(() => false), all.indexOf(document.activeElement as HTMLButtonElement), event.key);
    if (to === null) return;
    event.preventDefault();
    all[to]?.focus();
  };
  return (
    <div ref={root} className="relative">
      {trigger({ open, toggle })}
      {open ? (
        <ul ref={menu} role="menu" tabIndex={-1} onKeyDown={onKeyDown} style={fixed ? { position: "fixed", top: place?.top ?? 0, right: place?.right ?? 0, opacity: place ? 1 : 0 } : undefined} className={cn(fixed ? "z-50" : "absolute right-0 z-20", "rounded-osce-md border border-osce-border bg-surface p-1 shadow-lg", className)}>
          {children(closeToTrigger)}
        </ul>
      ) : null}
    </div>
  );
}
