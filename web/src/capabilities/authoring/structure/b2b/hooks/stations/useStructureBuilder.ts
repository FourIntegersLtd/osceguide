"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import type {
  StationBlockType,
  StationStructure,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  addBlock,
  addSection,
  type BuilderSelection,
  findBlockLocation,
  moveBlockAcrossSections,
  moveBlockWithinSection,
  parseDragId,
  removeSection,
  reorderSections,
} from "@/capabilities/authoring/structure/b2b/lib/stations/structureBuilderOps";

const MAX_UNDO = 50;

type DropTarget =
  | { kind: "section"; sectionId: string; index: number }
  | { kind: "sections-end"; index: number }
  | null;

function resolveActiveSectionFallback(
  sections: StationStructure["sections"],
  preferredId: string | null,
): string | null {
  if (sections.length === 0) return null;
  if (preferredId && sections.some((s) => s.id === preferredId)) {
    return preferredId;
  }
  return sections[0]?.id ?? null;
}

export function useStructureBuilder({
  value,
  onChange,
}: {
  value: StationStructure;
  onChange: (next: StationStructure) => void;
}) {
  const [selection, setSelection] = useState<BuilderSelection>({ kind: "none" });
  const [activeSectionId, setActiveSectionId] = useState<string | null>(() =>
    resolveActiveSectionFallback(value.sections, null),
  );
  const [showIds, setShowIds] = useState(false);
  const [activeDragId, setActiveDragId] = useState<string | null>(null);
  const [dropTarget, setDropTarget] = useState<DropTarget>(null);

  const undoStack = useRef<StationStructure[]>([]);
  const redoStack = useRef<StationStructure[]>([]);
  const skipHistory = useRef(false);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const syncHistoryFlags = useCallback(() => {
    setCanUndo(undoStack.current.length > 0);
    setCanRedo(redoStack.current.length > 0);
  }, []);

  const pushHistory = useCallback(
    (prev: StationStructure) => {
      undoStack.current = [...undoStack.current.slice(-(MAX_UNDO - 1)), prev];
      redoStack.current = [];
      syncHistoryFlags();
    },
    [syncHistoryFlags],
  );

  const applyChange = useCallback(
    (next: StationStructure, recordHistory = true) => {
      if (recordHistory && !skipHistory.current) {
        pushHistory(value);
      }
      onChange(next);
    },
    [onChange, pushHistory, value],
  );

  const undo = useCallback(() => {
    const prev = undoStack.current.pop();
    if (!prev) return;
    skipHistory.current = true;
    redoStack.current = [...redoStack.current, value];
    onChange(prev);
    skipHistory.current = false;
    syncHistoryFlags();
  }, [onChange, syncHistoryFlags, value]);

  const redo = useCallback(() => {
    const next = redoStack.current.pop();
    if (!next) return;
    skipHistory.current = true;
    undoStack.current = [...undoStack.current, value];
    onChange(next);
    skipHistory.current = false;
    syncHistoryFlags();
  }, [onChange, syncHistoryFlags, value]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelection({ kind: "none" });
        return;
      }
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (e.key === "z" && e.shiftKey) {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [redo, undo]);

  const [prevSections, setPrevSections] = useState(value.sections);
  if (prevSections !== value.sections) {
    setPrevSections(value.sections);
    setActiveSectionId((prev) =>
      resolveActiveSectionFallback(value.sections, prev),
    );
  }

  if (selection.kind === "section") {
    const exists = value.sections.some((s) => s.id === selection.sectionId);
    if (!exists) setSelection({ kind: "none" });
  }
  if (selection.kind === "block") {
    const loc = findBlockLocation(value, selection.blockId);
    if (!loc) setSelection({ kind: "none" });
  }

  const addBlockToTarget = useCallback(
    (type: StationBlockType, sectionId?: string, index?: number) => {
      const sid = sectionId ?? activeSectionId;
      if (!sid) {
        const withSection = addSection(value);
        const newSectionId =
          withSection.sections[withSection.sections.length - 1]?.id;
        if (!newSectionId) return;
        const next = addBlock(withSection, newSectionId, type);
        const block = next.sections
          .find((s) => s.id === newSectionId)
          ?.blocks.at(-1);
        applyChange(next);
        setActiveSectionId(newSectionId);
        if (block) {
          setSelection({
            kind: "block",
            sectionId: newSectionId,
            blockId: block.id,
          });
        }
        return;
      }
      const next = addBlock(value, sid, type, index);
      const target = next.sections.find((s) => s.id === sid);
      const block =
        index === undefined
          ? target?.blocks.at(-1)
          : target?.blocks[Math.min(index, (target.blocks.length || 1) - 1)];
      applyChange(next);
      setActiveSectionId(sid);
      if (block) {
        setSelection({ kind: "block", sectionId: sid, blockId: block.id });
      }
    },
    [activeSectionId, applyChange, value],
  );

  const handleAddSection = useCallback(() => {
    const next = addSection(value);
    const section = next.sections.at(-1);
    applyChange(next);
    if (section) {
      setActiveSectionId(section.id);
      setSelection({ kind: "none" });
    }
  }, [applyChange, value]);

  const handleRemoveSection = useCallback(
    (sectionId: string) => {
      const index = value.sections.findIndex((s) => s.id === sectionId);
      if (index < 0) return;
      const next = removeSection(value, sectionId);
      applyChange(next);
      setSelection({ kind: "none" });
      if (activeSectionId === sectionId) {
        const fallback =
          next.sections[index]?.id ??
          next.sections[index - 1]?.id ??
          next.sections[0]?.id ??
          null;
        setActiveSectionId(fallback);
      }
    },
    [activeSectionId, applyChange, value],
  );

  const focusSection = useCallback((sectionId: string) => {
    setActiveSectionId(sectionId);
    setSelection({ kind: "none" });
  }, []);

  const openSectionSettings = useCallback((sectionId: string) => {
    setActiveSectionId(sectionId);
    setSelection({ kind: "section", sectionId });
  }, []);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const resolveDropTarget = useCallback(
    (overId: string | null): DropTarget => {
      if (!overId) return null;
      if (overId.startsWith("drop-section:")) {
        const sectionId = overId.slice("drop-section:".length);
        const section = value.sections.find((s) => s.id === sectionId);
        return section
          ? { kind: "section", sectionId, index: section.blocks.length }
          : null;
      }
      const parsed = parseDragId(overId);
      if (parsed?.kind === "block" && parsed.sectionId && parsed.blockId) {
        const section = value.sections.find((s) => s.id === parsed.sectionId);
        const index =
          section?.blocks.findIndex((b) => b.id === parsed.blockId) ?? -1;
        if (section && index >= 0) {
          return { kind: "section", sectionId: parsed.sectionId, index };
        }
      }
      if (overId === "drop-sections-end") {
        return { kind: "sections-end", index: value.sections.length };
      }
      return null;
    },
    [value.sections],
  );

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveDragId(String(event.active.id));
  }, []);

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      setDropTarget(
        resolveDropTarget(event.over ? String(event.over.id) : null),
      );
    },
    [resolveDropTarget],
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const activeId = String(event.active.id);
      const overId = event.over ? String(event.over.id) : null;
      setActiveDragId(null);
      setDropTarget(null);
      if (!overId || activeId === overId) return;

      const parsedActive = parseDragId(activeId);

      if (parsedActive?.kind === "section") {
        const parsedOver = parseDragId(overId);
        if (parsedOver?.kind === "section") {
          const fromIndex = value.sections.findIndex(
            (s) => s.id === parsedActive.value,
          );
          const toIndex = value.sections.findIndex(
            (s) => s.id === parsedOver.value,
          );
          if (fromIndex >= 0 && toIndex >= 0) {
            applyChange(reorderSections(value, fromIndex, toIndex));
          }
        }
        return;
      }

      if (
        parsedActive?.kind === "block" &&
        parsedActive.sectionId &&
        parsedActive.blockId
      ) {
        const fromLoc = findBlockLocation(value, parsedActive.blockId);
        if (!fromLoc) return;

        if (overId.startsWith("drop-section:")) {
          const toSectionId = overId.slice("drop-section:".length);
          const toSection = value.sections.find((s) => s.id === toSectionId);
          if (!toSection) return;
          applyChange(
            moveBlockAcrossSections(
              value,
              fromLoc.sectionId,
              parsedActive.blockId,
              toSectionId,
              toSection.blocks.length,
            ),
          );
          setActiveSectionId(toSectionId);
          return;
        }

        const parsedOver = parseDragId(overId);
        if (
          parsedOver?.kind === "block" &&
          parsedOver.sectionId &&
          parsedOver.blockId
        ) {
          const toIndex =
            value.sections
              .find((s) => s.id === parsedOver.sectionId)
              ?.blocks.findIndex((b) => b.id === parsedOver.blockId) ?? -1;
          if (toIndex < 0) return;
          if (fromLoc.sectionId === parsedOver.sectionId) {
            applyChange(
              moveBlockWithinSection(
                value,
                fromLoc.sectionId,
                fromLoc.blockIndex,
                toIndex,
              ),
            );
          } else {
            applyChange(
              moveBlockAcrossSections(
                value,
                fromLoc.sectionId,
                parsedActive.blockId,
                parsedOver.sectionId,
                toIndex,
              ),
            );
            setActiveSectionId(parsedOver.sectionId);
          }
        }
      }
    },
    [applyChange, value],
  );

  const handleDragCancel = useCallback(() => {
    setActiveDragId(null);
    setDropTarget(null);
  }, []);

  return {
    selection,
    setSelection,
    activeSectionId,
    setActiveSectionId,
    focusSection,
    openSectionSettings,
    showIds,
    setShowIds,
    activeDragId,
    dropTarget,
    sensors,
    applyChange,
    addBlockToTarget,
    handleAddSection,
    handleRemoveSection,
    handleDragStart,
    handleDragOver,
    handleDragEnd,
    handleDragCancel,
    undo,
    redo,
    canUndo,
    canRedo,
  };
}
