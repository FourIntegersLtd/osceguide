"use client";

import { Button, Input } from "@/foundation/ui";
import { HiOutlinePlus, HiOutlineTrash } from "react-icons/hi2";

export function StringListField({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder?: string;
}) {
  const updateAt = (index: number, value: string) => {
    const next = [...items];
    next[index] = value;
    onChange(next);
  };

  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium text-ink">{label}</span>
      <ul className="flex flex-col gap-2">
        {items.map((line, index) => (
          <li key={index} className="flex gap-2">
            <Input
              aria-label={`${label} ${index + 1}`}
              value={line}
              placeholder={placeholder}
              onChange={(e) => updateAt(index, e.target.value)}
              className="flex-1"
            />
            <Button
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Remove ${label} ${index + 1}`}
              onClick={() => onChange(items.filter((_, i) => i !== index))}
            >
              <HiOutlineTrash className="h-4 w-4" aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
      <Button
        type="button"
        variant="secondary"
        size="sm"
        className="w-fit gap-1"
        onClick={() => onChange([...items, ""])}
      >
        <HiOutlinePlus className="h-4 w-4" aria-hidden />
        Add line
      </Button>
    </div>
  );
}
