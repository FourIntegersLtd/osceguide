"use client";

import { Textarea } from "@/foundation/ui";
import { useId, useState } from "react";
import { HiOutlinePencilSquare, HiOutlineXMark } from "react-icons/hi2";
import { B2BButton } from "@/capabilities/authoring/structure/b2b/components/ui/B2BButton";

/** List block editor — matches B2C admin station update (items + Add new item). */
export function StationInstanceArrayField({
  label,
  required,
  items,
  readOnly,
  onChange,
}: {
  label: string;
  required?: boolean;
  items: string[];
  readOnly?: boolean;
  onChange: (next: string[]) => void;
}) {
  const labelId = useId();
  const [newItem, setNewItem] = useState("");
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");

  function commitEdit(index: number) {
    const next = [...items];
    next[index] = editValue;
    onChange(next);
    setEditingIndex(null);
    setEditValue("");
  }

  /*
    What is typed in the add box is already the list's last item, so the form counts as edited and
    Save stores it whether or not Add was pressed. Add (or leaving the box) tidies it and empties
    the box for the next one. `items` is checked rather than a flag, so a list replaced from
    outside never has its last item mistaken for the box.
  */
  const pending = newItem !== "" && items[items.length - 1] === newItem;
  const listed = pending ? items.slice(0, -1) : items;

  function typeItem(text: string) {
    setNewItem(text);
    if (pending) onChange(text.trim() ? [...listed, text] : listed);
    else if (text.trim()) onChange([...items, text]);
  }

  function addItem() {
    if (!pending) return;
    onChange([...listed, newItem.trim()]);
    setNewItem("");
  }

  const ro = !!readOnly;

  return (
    <div className="min-w-0 md:col-span-2 space-y-1.5" role="group" aria-labelledby={labelId}>
      <p id={labelId} className="block text-osce-body font-medium text-ink">
        {label}
        {required ? <span className="text-osce-danger-text"> *</span> : null}
      </p>
      <div className="space-y-1.5">
        {listed.length === 0 && !ro ? (
          <p className="rounded-osce-md border border-border px-3 py-2 text-osce-body text-ink-muted">
            None
          </p>
        ) : null}
        {listed.map((item, index) => (
          <div key={`${index}-${item.slice(0, 24)}`} className="group flex gap-1.5">
            {editingIndex === index ? (
              <Textarea
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => commitEdit(index)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    commitEdit(index);
                  }
                }}
                aria-label={`Edit ${label} item ${index + 1}`}
                rows={Math.max(3, Math.min(8, editValue.split("\n").length + 1))}
                className="min-h-[4.5rem] flex-1 resize-y"
                // Opened by the Edit action, so focus moves into what it opened.
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
                disabled={ro}
              />
            ) : (
              <span
                className="flex-1 whitespace-pre-wrap rounded-osce-md border border-border px-3 py-2 text-osce-body text-ink transition-colors group-hover:border-accent/40"
              >
                {item}
              </span>
            )}
            {!ro ? (
              <>
                <button
                  type="button"
                  onClick={() => {
                    if (editingIndex === index) {
                      commitEdit(index);
                    } else {
                      setEditingIndex(index);
                      setEditValue(item);
                    }
                  }}
                  className={`rounded-osce-md p-1.5 text-osce-body transition-colors ${
                    editingIndex === index
                      ? "text-accent hover:bg-surface-raised"
                      : "text-accent hover:bg-surface-raised"
                  }`}
                  aria-label={`Edit ${label} item ${index + 1}`}
                >
                  <HiOutlinePencilSquare className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => onChange(items.filter((_, i) => i !== index))}
                  className="rounded-osce-md p-1.5 text-danger transition-colors hover:bg-osce-danger-bg"
                  aria-label={`Remove ${label} item ${index + 1}`}
                >
                  <HiOutlineXMark className="h-3.5 w-3.5" />
                </button>
              </>
            ) : null}
          </div>
        ))}
        {!ro ? (
          <div className="flex gap-1.5">
            <Textarea
              value={newItem}
              onChange={(e) => typeItem(e.target.value)}
              onBlur={addItem}
              aria-label={`${label}: add new item`}
              rows={3}
              className="min-h-[4.5rem] flex-1 resize-y"
              placeholder="Add new item"
            />
            <B2BButton type="button" variant="commit" className="self-end" onClick={addItem}>
              Add
            </B2BButton>
          </div>
        ) : null}
      </div>
    </div>
  );
}
