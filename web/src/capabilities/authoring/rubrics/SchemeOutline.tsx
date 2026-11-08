"use client";

import { useEffect, useState } from "react";
import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Alert, Badge, ConfirmModal, Modal, PopupMenu, cn } from "@/foundation/ui";
import { AuthoringButton } from "@/capabilities/authoring/parts/AuthoringButton";
import { pathText } from "@/capabilities/authoring/rubrics/jsonPath";
import { revealPath } from "@/capabilities/authoring/rubrics/ProblemList";
import { AddMenu, type AddChoice } from "@/capabilities/authoring/rubrics/AddMenu";
import { CompetencyDetail, CustomDetail, DomainDetail, NotesDetail } from "@/capabilities/authoring/rubrics/DomainBlock";
import {
  addCompetency,
  addDomain,
  addNotes,
  cannotShow,
  FEEDBACK_KIND_WORDS,
  FEEDBACK_SHAPE_WORDS,
  isCustom,
  duplicateBlock,
  duplicateCompetency,
  moveBlock,
  moveCompetency,
  problemsWithin,
  remapFocus,
  removeBlock,
  removeCompetency,
  updateBlock,
  updateCompetency,
  type Block,
  type OutlineChange,
  type OutlineFocus,
  type Problem,
  type Scheme,
  type SchemeTabId,
} from "@/capabilities/authoring/rubrics/schemeModel";

type Focus = OutlineFocus;
/** Asks the outline to open the row a problem names and focus its field. */
export interface RevealRequest { path: string; nonce: number }
const ROW_PATH = /^outline\[(\d+)\](?:\.competencies\[(\d+)\])?(\..*)?$/;
type Pending = { kind: "block"; i: number } | { kind: "competency"; i: number; j: number };

function RowMenu({ label, canUp, canDown, canDelete, onUp, onDown, onDuplicate, onDelete }: { label: string; canUp: boolean; canDown: boolean; canDelete: boolean; onUp: () => void; onDown: () => void; onDuplicate?: () => void; onDelete: () => void }) {
  const item = "flex min-h-9 w-full items-center rounded px-3 text-left text-osce-body text-ink hover:bg-osce-canvas disabled:text-ink-subtle";
  return (
    <PopupMenu
      className="w-40"
      trigger={({ open, toggle }) => (
        <button type="button" aria-label={`More for ${label}`} aria-haspopup="menu" aria-expanded={open} className="min-h-9 min-w-9 rounded text-ink-muted hover:bg-osce-canvas" onClick={toggle}>
          ⋯
        </button>
      )}
    >
      {(close) => {
        const run = (fn: () => void) => () => {
          close();
          fn();
        };
        return (
          <>
            <li role="none"><button role="menuitem" type="button" className={item} disabled={!canUp} onClick={run(onUp)}>Move up</button></li>
            <li role="none"><button role="menuitem" type="button" className={item} disabled={!canDown} onClick={run(onDown)}>Move down</button></li>
            {onDuplicate ? <li role="none"><button role="menuitem" type="button" className={item} onClick={run(onDuplicate)}>Duplicate</button></li> : null}
            <li role="none"><button role="menuitem" type="button" className={item} disabled={!canDelete} onClick={run(onDelete)}>Delete</button></li>
          </>
        );
      }}
    </PopupMenu>
  );
}

function Row({ id, path, name, nested, selected, children }: { id: string; path: string; name: string; nested?: boolean; selected: boolean; children: (handle: React.ReactNode) => React.ReactNode }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });
  const handle = (
    <button type="button" aria-label={`Drag ${name} to reorder`} className="min-h-9 min-w-6 cursor-grab touch-none text-ink-subtle" {...attributes} {...listeners}>
      ⋮⋮
    </button>
  );
  return (
    <div
      ref={setNodeRef}
      data-path={path}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={cn("flex items-center gap-1 rounded-osce-md border px-2", nested && "ml-6", selected ? "border-accent bg-osce-accent-subtle" : "border-osce-border bg-surface", isDragging && "opacity-60")}
    >
      {children(handle)}
    </div>
  );
}

/** The outline: domains, their competencies and notes, each draggable, with the detail of the picked row. */
export function SchemeOutline({ scheme, onScheme, readOnly, problems, reveal, onJump, onEditCustom }: { scheme: Scheme; onScheme: (s: Scheme) => void; readOnly: boolean; problems: readonly Problem[]; reveal: RevealRequest | null; onJump: (tab: SchemeTabId) => void; onEditCustom: () => void }) {
  const [focus, setFocus] = useState<Focus | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  // As on the board, only the first domain starts open; the picked one is always open.
  const firstDomain = scheme.outline.find((b) => b.block === "domain");
  const [toggled, setToggled] = useState<ReadonlyMap<string, boolean>>(new Map());
  const isOpen = (b: Block, i: number) => b.block === "domain" && (toggled.get(b.id) ?? (b === firstDomain)) || focus?.block === i && b.block === "domain";
  const flip = (b: Block, i: number) => {
    if (b.block !== "domain") return;
    if (isOpen(b, i) && focus?.block === i) setFocus(null);
    setToggled(new Map(toggled).set(b.id, !isOpen(b, i)));
  };
  // The detail is always a modal, opened only by Details (or a problem pointing into it), so it is seen opening.
  /** Apply an edit that moves rows, keeping the picked row on the row it was on. */
  const edit = (next: Scheme, change: OutlineChange) => {
    setFocus((current) => remapFocus(current, change));
    onScheme(next);
  };
  useEffect(() => {
    const hit = reveal ? ROW_PATH.exec(reveal.path) : null;
    if (!reveal || !hit) return;
    const block = Number(hit[1]);
    const competency = hit[2] === undefined ? undefined : Number(hit[2]);
    const row = scheme.outline[block];
    if (row?.block === "domain") setToggled((t) => new Map(t).set(row.id, true));
    // Only a problem in the detail fields opens it; the row's own title or label is focused where it stands.
    if (!/^(\.(title|label))?$/.test(hit[3] ?? "")) setFocus(competency === undefined ? { block } : { block, competency });
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => revealPath(reveal.path)));
  }, [reveal?.nonce]); // eslint-disable-line react-hooks/exhaustive-deps -- runs once per request
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }), useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }));
  const ids = scheme.outline.map((b, i) => `block:${b.block === "custom" ? `custom-${i}` : b.id}`);
  const compId = (i: number, j: number) => {
    const b = scheme.outline[i];
    return b?.block === "domain" ? `comp:${b.id}:${b.competencies[j]?.id}` : "";
  };

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return;
    const a = String(active.id);
    const o = String(over.id);
    if (a.startsWith("block:") && o.startsWith("block:")) {
      const [from, to] = [ids.indexOf(a), ids.indexOf(o)];
      return edit(moveBlock(scheme, from, to), { kind: "move", from, to });
    }
    if (a.startsWith("comp:") && o.startsWith("comp:")) {
      const i = scheme.outline.findIndex((b) => b.block === "domain" && a.startsWith(`comp:${b.id}:`));
      const b = scheme.outline[i];
      if (b?.block !== "domain" || !o.startsWith(`comp:${b.id}:`)) return;
      const [from, to] = [b.competencies.findIndex((_, j) => compId(i, j) === a), b.competencies.findIndex((_, j) => compId(i, j) === o)];
      edit(moveCompetency(scheme, i, from, to), { kind: "moveCompetency", block: i, from, to });
    }
  };

  const choose = (choice: AddChoice) => {
    if (choice === "domain") {
      onScheme(addDomain(scheme));
      return setFocus({ block: scheme.outline.length });
    }
    if (choice === "notes") {
      onScheme(addNotes(scheme));
      return setFocus({ block: scheme.outline.length });
    }
    if (choice === "competency") {
      if (focus === null || scheme.outline[focus.block]?.block !== "domain") return;
      const count = (scheme.outline[focus.block] as { competencies: unknown[] }).competencies.length;
      onScheme(addCompetency(scheme, focus.block));
      return setFocus({ block: focus.block, competency: count });
    }
    onJump(choice);
  };

  const confirmDelete = () => {
    if (!pending) return;
    if (pending.kind === "block") edit(removeBlock(scheme, pending.i), { kind: "remove", at: pending.i });
    else edit(removeCompetency(scheme, pending.i, pending.j), { kind: "removeCompetency", block: pending.i, at: pending.j });
    setPending(null);
  };

  const block = focus ? scheme.outline[focus.block] : undefined;
  const detail = !focus || !block ? null : block.block === "custom" ? (
    <CustomDetail onEditCustom={onEditCustom} />
  ) : focus.competency !== undefined && block.block === "domain" ? (
    <CompetencyDetail scheme={scheme} onScheme={onScheme} readOnly={readOnly} i={focus.block} j={focus.competency} onDelete={() => setPending({ kind: "competency", i: focus.block, j: focus.competency as number })} />
  ) : block.block === "domain" ? (
    <DomainDetail scheme={scheme} onScheme={onScheme} readOnly={readOnly} onEditCustom={onEditCustom} i={focus.block} onDelete={() => setPending({ kind: "block", i: focus.block })} />
  ) : (
    <NotesDetail scheme={scheme} onScheme={onScheme} readOnly={readOnly} onEditCustom={onEditCustom} i={focus.block} onDelete={() => setPending({ kind: "block", i: focus.block })} />
  );
  const focusedDomain = block?.block === "domain";
  const titleInput = "min-w-0 flex-1 border-0 bg-transparent px-1 text-osce-body text-ink focus:outline-none";

  if (cannotShow(scheme)) {
    return (
      <div className="space-y-3 rounded-osce-md border border-osce-border p-4">
        <h2 className="text-osce-body font-semibold text-ink">Domains</h2>
        <Alert tone="info">
          The builder cannot show this marking scheme. Edit it as JSON under Advanced.{" "}
          <AuthoringButton variant="ghost" size="sm" onClick={onEditCustom}>Open the JSON</AuthoringButton>
        </Alert>
        <p className="text-osce-caption text-ink-muted">Rating scale, Pass rule and Feedback cannot be shown for this scheme. Edit it on the Advanced tab.</p>
      </div>
    );
  }

  const pickedBlock = pending ? scheme.outline[pending.i] : undefined;
  const deleting = (() => {
    if (!pending || !pickedBlock) return { title: "", body: "" };
    if (pending.kind === "competency" && pickedBlock.block === "domain") {
      return { title: `Delete ${pickedBlock.competencies[pending.j]?.label ?? "this competency"}?`, body: "Its instructions and level descriptions go too. To bring it back, leave without saving." };
    }
    if (pickedBlock.block === "domain") {
      const n = pickedBlock.competencies.length;
      return { title: `Delete ${pickedBlock.title || "this domain"}?`, body: `Its ${n} ${n === 1 ? "competency" : "competencies"} and their instructions go too. To bring it back, leave without saving.` };
    }
    return { title: `Delete ${pickedBlock.block === "notes" ? pickedBlock.title || "this notes block" : "this block"}?`, body: "Everything the marker writes there goes too, including its custom field. To bring it back, leave without saving." };
  })();
  const detailKind = !block ? "" : block.block === "custom" ? "Custom field" : focus?.competency !== undefined && block.block === "domain" ? `Competency in ${block.title || block.id}` : block.block === "domain" ? "Domain" : "Notes";

  return (
    <div className="space-y-3" data-path="outline">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-osce-body font-semibold text-ink">Domains and competencies</h2>
        {readOnly ? null : <AddMenu canAddCompetency={focusedDomain} onChoose={choose} />}
      </div>
      {scheme.outline.length === 0 ? <p className="rounded-osce-md bg-osce-canvas px-3 py-4 text-osce-meta text-ink-muted">Nothing here yet. Add a domain to start.</p> : null}
      <div className="space-y-4">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={ids} strategy={verticalListSortingStrategy}>
            <div className="space-y-2">
              {scheme.outline.map((b, i) => {
                const label = b.block === "custom" ? "Custom block" : b.title || b.id;
                const count = problemsWithin(problems, ["outline", i]);
                const picked = focus?.block === i && focus.competency === undefined;
                return (
                  <div key={ids[i]} className="space-y-2">
                    <Row id={ids[i] as string} path={pathText(["outline", i])} name={label} selected={picked}>
                      {(handle) => (
                        <>
                          {readOnly ? null : handle}
                          {b.block === "domain" ? (
                            <button type="button" aria-expanded={isOpen(b, i)} aria-label={`${isOpen(b, i) ? "Hide" : "Show"} competencies of ${label}`} className="min-h-9 min-w-6 text-ink-muted" onClick={() => flip(b, i)}>{isOpen(b, i) ? "▾" : "▸"}</button>
                          ) : null}
                          {b.block === "custom" ? (
                            <button type="button" className="min-h-11 flex-1 text-left text-osce-body text-ink-muted" onClick={() => setFocus({ block: i })}>Custom block</button>
                          ) : (
                            <input aria-label={`Title of ${b.block} ${i + 1}`} data-path={pathText(["outline", i, "title"])} className={titleInput} readOnly={readOnly} value={b.title ?? ""} onChange={(event) => onScheme(updateBlock(scheme, i, { title: event.target.value }))} />
                          )}
                          <Badge variant="neutral" className="shrink-0">{b.block === "domain" ? `${b.competencies.length} ${b.competencies.length === 1 ? "competency" : "competencies"}` : b.block === "notes" ? "Notes" : "Custom"}</Badge>
                          {count > 0 ? <Badge variant="danger">{count}</Badge> : null}
                          <AuthoringButton variant="ghost" size="sm" aria-label={`Details of ${label}`} onClick={() => setFocus({ block: i })}>Details</AuthoringButton>
                          {readOnly ? null : (
                            <RowMenu label={label} canUp={i > 0} canDown={i < scheme.outline.length - 1} canDelete={b.block !== "custom"} onUp={() => edit(moveBlock(scheme, i, i - 1), { kind: "move", from: i, to: i - 1 })} onDown={() => edit(moveBlock(scheme, i, i + 1), { kind: "move", from: i, to: i + 1 })} onDuplicate={b.block === "custom" ? undefined : () => edit(duplicateBlock(scheme, i), { kind: "insert", at: i + 1 })} onDelete={() => setPending({ kind: "block", i })} />
                          )}
                        </>
                      )}
                    </Row>
                    {b.block === "notes" ? b.feedback.map((item, k) => (
                      <div key={`${ids[i]}:${k}`} className="ml-6 flex items-center gap-2 rounded-osce-md border border-osce-border px-3 py-2 text-osce-meta text-ink-muted">
                        <span className="text-ink">{isCustom(item) ? "Custom field" : item.label || FEEDBACK_KIND_WORDS[item.kind]}</span>
                        <span>{isCustom(item) ? "Kept as it is" : `${FEEDBACK_KIND_WORDS[item.kind]} · ${FEEDBACK_SHAPE_WORDS[item.shape]}`}</span>
                      </div>
                    )) : null}
                    {b.block === "domain" && isOpen(b, i) ? (
                      <SortableContext items={b.competencies.map((_, j) => compId(i, j))} strategy={verticalListSortingStrategy}>
                        <div className="space-y-2">
                          {b.competencies.map((c, j) => {
                            const cc = problemsWithin(problems, ["outline", i, "competencies", j]);
                            return (
                              <Row key={compId(i, j)} id={compId(i, j)} path={pathText(["outline", i, "competencies", j])} name={c.label || `competency ${j + 1}`} nested selected={focus?.block === i && focus.competency === j}>
                                {(handle) => (
                                  <>
                                    {readOnly ? null : handle}
                                    <input aria-label={`Competency ${j + 1} of ${label}`} data-path={pathText(["outline", i, "competencies", j, "label"])} className={titleInput} readOnly={readOnly} value={c.label} onChange={(event) => onScheme(updateCompetency(scheme, i, j, { label: event.target.value }))} />
                                    {cc > 0 ? <Badge variant="danger">{cc}</Badge> : null}
                                    <AuthoringButton variant="ghost" size="sm" aria-label={`Details of ${c.label}`} onClick={() => setFocus({ block: i, competency: j })}>Details</AuthoringButton>
                                    {readOnly ? null : (
                                      <RowMenu label={c.label} canUp={j > 0} canDown={j < b.competencies.length - 1} canDelete={b.competencies.length > 1} onUp={() => edit(moveCompetency(scheme, i, j, j - 1), { kind: "moveCompetency", block: i, from: j, to: j - 1 })} onDown={() => edit(moveCompetency(scheme, i, j, j + 1), { kind: "moveCompetency", block: i, from: j, to: j + 1 })} onDuplicate={() => edit(duplicateCompetency(scheme, i, j), { kind: "insertCompetency", block: i, at: j + 1 })} onDelete={() => setPending({ kind: "competency", i, j })} />
                                    )}
                                  </>
                                )}
                              </Row>
                            );
                          })}
                          {readOnly ? null : (
                            <AuthoringButton variant="ghost" size="sm" className="ml-6" onClick={() => { onScheme(addCompetency(scheme, i)); setFocus({ block: i, competency: b.competencies.length }); }}>
                              Add competency
                            </AuthoringButton>
                          )}
                        </div>
                      </SortableContext>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </SortableContext>
        </DndContext>
      </div>
      {detail ? (
        <Modal onClose={() => setFocus(null)} title={detailKind}>
          {detail}
        </Modal>
      ) : null}
      <ConfirmModal
        isOpen={pending !== null}
        onCancel={() => setPending(null)}
        onConfirm={confirmDelete}
        title={deleting.title}
        message={deleting.body}
        confirmText="Delete"
        tone="danger"
      />
    </div>
  );
}
