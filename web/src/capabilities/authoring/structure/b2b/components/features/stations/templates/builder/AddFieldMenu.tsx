"use client";

import {
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { HiOutlineInformationCircle, HiPlus } from "react-icons/hi2";
import {
  formsOrderForKind,
  STATION_BLOCK_FORMS_GROUPS,
  type StationBlockFormsGroup,
  type TemplateKind,
} from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationBlockType } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { b2bInputBase } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import {
  builderUi,
  ToneBadge,
  type BuilderTone,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";

const PANEL_WIDTH = 300;
const GAP = 6;
const PAD = 8;

const GROUP_TONE: Record<StationBlockFormsGroup, BuilderTone> = {
  text: "primary",
  rich: "violet",
  choices: "emerald",
  scoring: "amber",
};

function panelPosition(trigger: HTMLElement, panel: HTMLElement | null): CSSProperties {
  const rect = trigger.getBoundingClientRect();
  const height = panel?.offsetHeight ?? 360;
  const spaceBelow = window.innerHeight - rect.bottom - PAD;
  const openUp = spaceBelow < height + GAP && rect.top - PAD > spaceBelow;
  const left = Math.max(
    PAD,
    Math.min(rect.left, window.innerWidth - PANEL_WIDTH - PAD),
  );
  return {
    position: "fixed",
    left,
    top: openUp
      ? Math.max(PAD, rect.top - GAP - height)
      : Math.min(window.innerHeight - PAD, rect.bottom + GAP),
    width: PANEL_WIDTH,
    zIndex: 200,
  };
}

/**
 * Grouped "Add field" picker (Google Forms / Notion pattern). Renders in a
 * portal so it is never clipped by the stage's scroll container.
 */
export function AddFieldMenu({
  kind,
  onPick,
  onOpenFieldTypesInfo,
  trigger,
}: {
  kind: TemplateKind;
  onPick: (type: StationBlockType) => void;
  onOpenFieldTypesInfo: () => void;
  /** Render prop for the trigger; receives open state and the toggle handler. */
  trigger: (props: {
    open: boolean;
    toggle: () => void;
    ref: (el: HTMLElement | null) => void;
    "aria-haspopup": "menu";
    "aria-expanded": boolean;
    "aria-controls": string;
  }) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [style, setStyle] = useState<CSSProperties>({});
  const [triggerEl, setTriggerEl] = useState<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const menuId = useId();

  const close = useCallback(() => {
    setOpen(false);
    setQuery("");
  }, []);
  const toggle = useCallback(() => setOpen((prev) => !prev), []);

  const reposition = useCallback(() => {
    if (!triggerEl) return;
    setStyle(panelPosition(triggerEl, panelRef.current));
  }, [triggerEl]);

  useLayoutEffect(() => {
    if (!open) return;
    reposition();
    searchRef.current?.focus();
  }, [open, reposition]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target)) return;
      if (triggerEl?.contains(target)) return;
      close();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        close();
        triggerEl?.focus();
      }
    };
    window.addEventListener("mousedown", onPointer);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      window.removeEventListener("mousedown", onPointer);
      window.removeEventListener("keydown", onKey, true);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [open, close, reposition, triggerEl]);

  const q = query.trim().toLowerCase();
  const matches = (label: string, description: string) =>
    !q || label.toLowerCase().includes(q) || description.toLowerCase().includes(q);
  const groups = STATION_BLOCK_FORMS_GROUPS.map((group) => ({
    ...group,
    items: formsOrderForKind(kind).filter(
      (m) => m.group === group.id && matches(m.formsLabel, m.description),
    ),
  })).filter((g) => g.items.length > 0);

  const pick = (type: StationBlockType) => {
    onPick(type);
    close();
  };

  return (
    <>
      {trigger({
        open,
        toggle,
        ref: setTriggerEl,
        "aria-haspopup": "menu",
        "aria-expanded": open,
        "aria-controls": menuId,
      })}
      {open && typeof document !== "undefined"
        ? createPortal(
            // Stops a click inside the menu reaching the outside-click closer; not an action.
            // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus
            <div
              ref={panelRef}
              id={menuId}
              role="menu"
              aria-label="Add a field"
              style={style}
              className={`osce-builder-in flex max-h-[min(70vh,30rem)] flex-col overflow-hidden rounded-2xl shadow-xl ${builderUi.box} ${builderUi.surface}`}
              onClick={(e) => e.stopPropagation()}
            >
              <div className={`px-3 pb-2 pt-3 ${builderUi.b}`}>
                <p className={`mb-2 ${builderUi.eyebrow}`}>Add a field</p>
                <input
                  ref={searchRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search field types…"
                  aria-label="Search field types"
                  className={`${b2bInputBase} py-1.5 text-osce-body`}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      const first = groups[0]?.items[0];
                      if (first) pick(first.type);
                    }
                  }}
                />
              </div>
              <div className="min-h-0 flex-1 overflow-y-auto p-1.5">
                {groups.length === 0 ? (
                  <p className="px-3 py-4 text-center text-osce-caption text-ink-subtle">
                    No field type matches “{query}”.
                  </p>
                ) : (
                  groups.map((group) => (
                    <div key={group.id} role="group" aria-label={group.label}>
                      <p className={`px-2.5 pb-1 pt-2.5 ${builderUi.eyebrow}`}>
                        {group.label}
                      </p>
                      {group.items.map((meta) => {
                        const Icon = meta.icon;
                        return (
                          <button
                            key={meta.type}
                            type="button"
                            role="menuitem"
                            title={meta.description}
                            onClick={() => pick(meta.type)}
                            className={`flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left transition-colors hover:bg-osce-canvas focus:bg-osce-canvas focus:outline-none`}
                          >
                            <ToneBadge tone={GROUP_TONE[group.id]} size="sm">
                              <Icon aria-hidden />
                            </ToneBadge>
                            <span className="min-w-0 flex-1">
                              <span className="block text-osce-body font-medium text-ink-muted">
                                {meta.formsLabel}
                              </span>
                              <span className="block truncate text-osce-caption text-ink-subtle">
                                {meta.description}
                              </span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={() => {
                  close();
                  onOpenFieldTypesInfo();
                }}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-left text-osce-caption font-medium text-ink-muted transition-colors hover:bg-osce-canvas hover:text-ink-muted ${builderUi.t}`}
              >
                <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
                Field type guide
              </button>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}

/** Full-width dashed "Add field" button used at the end of a section. */
export function AddFieldButton({
  kind,
  onPick,
  onOpenFieldTypesInfo,
}: {
  kind: TemplateKind;
  onPick: (type: StationBlockType) => void;
  onOpenFieldTypesInfo: () => void;
}) {
  return (
    <AddFieldMenu
      kind={kind}
      onPick={onPick}
      onOpenFieldTypesInfo={onOpenFieldTypesInfo}
      trigger={({ toggle, ref, open, ...aria }) => (
        <button
          ref={ref}
          type="button"
          {...aria}
          onClick={(e) => {
            e.stopPropagation();
            toggle();
          }}
          className={`flex w-full items-center justify-center gap-2 rounded-xl border border-dashed px-3 py-3 text-osce-body font-medium transition-colors ${builderUi.focusRing} ${
            open
              ? "border-osce-accent bg-osce-accent-muted text-osce-accent"
              : "border-osce-border text-ink-muted hover:border-osce-accent-subtle hover:bg-osce-accent-muted/60 hover:text-osce-accent"
          }`}
        >
          <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-osce-accent text-white">
            <HiPlus className="h-3.5 w-3.5" aria-hidden />
          </span>
          Add field
        </button>
      )}
    />
  );
}

/** Hairline "+" that appears between two rows on hover / focus. */
export function InsertFieldBetween({
  kind,
  onPick,
  onOpenFieldTypesInfo,
}: {
  kind: TemplateKind;
  onPick: (type: StationBlockType) => void;
  onOpenFieldTypesInfo: () => void;
}) {
  return (
    <AddFieldMenu
      kind={kind}
      onPick={onPick}
      onOpenFieldTypesInfo={onOpenFieldTypesInfo}
      trigger={({ toggle, ref, open, ...aria }) => (
        <div
          className={`relative z-10 -my-2 flex h-4 items-center justify-center transition-opacity ${
            open ? "opacity-100" : "opacity-0 hover:opacity-100 focus-within:opacity-100"
          }`}
        >
          <span className="absolute inset-x-5 h-px bg-osce-accent/50" aria-hidden />
          <button
            ref={ref}
            type="button"
            {...aria}
            aria-label="Insert field here"
            title="Insert field here"
            onClick={(e) => {
              e.stopPropagation();
              toggle();
            }}
            className={`relative inline-flex h-5 w-5 items-center justify-center rounded-full bg-osce-accent text-white shadow-sm hover:bg-osce-accent-hover ${builderUi.focusRing}`}
          >
            <HiPlus className="h-3 w-3" aria-hidden />
          </button>
        </div>
      )}
    />
  );
}
