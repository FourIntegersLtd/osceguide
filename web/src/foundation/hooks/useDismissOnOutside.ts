import { useEffect, type RefObject } from "react";

/** Whether an event closes an open popup: a press outside it, or Escape. */
export function dismisses(event: { type: "pointerdown"; inside: boolean } | { type: "keydown"; key: string }): boolean {
  return event.type === "pointerdown" ? !event.inside : event.key === "Escape";
}

/** While `open`, calls `onDismiss` for a press outside `ref` or the Escape key. */
export function useDismissOnOutside(ref: RefObject<HTMLElement | null>, open: boolean, onDismiss: () => void): void {
  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (dismisses({ type: "pointerdown", inside: Boolean(ref.current?.contains(event.target as Node)) })) onDismiss();
    };
    const onKey = (event: KeyboardEvent) => {
      if (dismisses({ type: "keydown", key: event.key })) onDismiss();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [ref, open, onDismiss]);
}
