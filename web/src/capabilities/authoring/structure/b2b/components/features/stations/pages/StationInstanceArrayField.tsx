"use client";

import { useState } from "react";
import { HiOutlinePencilSquare, HiOutlineXMark } from "react-icons/hi2";
import { B2BButton } from "@/capabilities/authoring/structure/b2b/components/ui/B2BButton";
import { b2bInputBase } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";

const multilineInputClass = `${b2bInputBase} min-h-[4.5rem] resize-y`;

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

  function addItem() {
    const trimmed = newItem.trim();
    if (!trimmed) return;
    onChange([...items, trimmed]);
    setNewItem("");
  }

  const ro = !!readOnly;

  return (
    <div className="min-w-0 md:col-span-2 space-y-1.5">
      <label className="block text-osce-body font-medium text-b2b-headline">
        {label}
        {required ? <span className="text-b2b-danger-text"> *</span> : null}
      </label>
      <div className="space-y-1.5">
        {items.length === 0 && !ro ? (
          <p className="rounded-md border border-b2b-border px-3 py-2 text-osce-body text-b2b-mid">
            None
          </p>
        ) : null}
        {items.map((item, index) => (
          <div key={`${index}-${item.slice(0, 24)}`} className="group flex gap-1.5">
            {editingIndex === index ? (
              <textarea
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onBlur={() => commitEdit(index)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    commitEdit(index);
                  }
                }}
                rows={Math.max(3, Math.min(8, editValue.split("\n").length + 1))}
                className={`flex-1 ${multilineInputClass}`}
                // Opened by the Edit action, so focus moves into what it opened.
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
                disabled={ro}
              />
            ) : (
              <span
                className="flex-1 whitespace-pre-wrap rounded-md border border-b2b-border px-3 py-2 text-osce-body text-b2b-headline transition-colors group-hover:border-b2b-accent/40"
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
                  className={`rounded-md p-1.5 text-osce-body transition-colors ${
                    editingIndex === index
                      ? "text-b2b-accent hover:bg-b2b-cream"
                      : "text-b2b-accent hover:bg-b2b-cream"
                  }`}
                  aria-label="Edit item"
                >
                  <HiOutlinePencilSquare className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => onChange(items.filter((_, i) => i !== index))}
                  className="rounded-md p-1.5 text-b2b-danger transition-colors hover:bg-b2b-danger-bg"
                  aria-label="Remove item"
                >
                  <HiOutlineXMark className="h-3.5 w-3.5" />
                </button>
              </>
            ) : null}
          </div>
        ))}
        {!ro ? (
          <div className="flex gap-1.5">
            <textarea
              value={newItem}
              onChange={(e) => setNewItem(e.target.value)}
              rows={3}
              className={`flex-1 ${multilineInputClass}`}
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
