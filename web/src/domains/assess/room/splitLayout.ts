/** The room card's splitter: width limits, keyboard steps, and what is remembered in this browser. */
export const SPLIT = { min: 280, max: 560, initial: 380, minMain: 360, storageKey: "osce.room.split.v1" } as const;

export interface SplitState {
  width: number;
  collapsed: boolean;
}

type Store = Pick<Storage, "getItem" | "setItem">;

/** The panel never goes below its minimum or above its maximum, and never squeezes the tiles under theirs. */
export function clampWidth(width: number, containerWidth?: number): number {
  const room = containerWidth === undefined ? SPLIT.max : Math.max(SPLIT.min, containerWidth - SPLIT.minMain);
  const value = Number.isFinite(width) ? width : SPLIT.initial;
  return Math.round(Math.min(Math.max(value, SPLIT.min), Math.min(SPLIT.max, room)));
}

/** Arrow keys resize (left widens a right-hand panel); shift takes a bigger step. */
export function stepWidth(width: number, key: string, shift: boolean, containerWidth?: number): number {
  const step = shift ? 64 : 16;
  if (key === "ArrowLeft") return clampWidth(width + step, containerWidth);
  if (key === "ArrowRight") return clampWidth(width - step, containerWidth);
  return width;
}

export function loadSplit(store?: Store): SplitState {
  try {
    const raw = (store ?? window.localStorage).getItem(SPLIT.storageKey);
    const parsed: unknown = raw ? JSON.parse(raw) : null;
    if (parsed && typeof parsed === "object") {
      const { width, collapsed } = parsed as Partial<SplitState>;
      return { width: clampWidth(typeof width === "number" ? width : SPLIT.initial), collapsed: collapsed === true };
    }
  } catch {
    /* blocked or broken storage: use the default */
  }
  return { width: SPLIT.initial, collapsed: false };
}

export function saveSplit(state: SplitState, store?: Store): void {
  try {
    (store ?? window.localStorage).setItem(SPLIT.storageKey, JSON.stringify(state));
  } catch {
    /* private window: the layout still works, it is just not remembered */
  }
}
