"use client";

import { useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { LuSearch } from "react-icons/lu";
import Modal from "@/foundation/ui/Modal";
import { cn } from "@/foundation/ui";
import type { NavItem } from "@/surfaces/contract";
import { matchingSections, moveActive } from "@/surfaces/jumpTo";

/**
 * The ⌘K palette behind the toolbar's search pill: type a section's name and
 * go there. It searches the nav you can see, nothing more.
 */
export function WorkspaceJumpTo({ items, onClose }: { items: NavItem[]; onClose: () => void }) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);

  const matches = useMemo(() => matchingSections(items, query), [items, query]);

  const go = (item: NavItem | undefined) => {
    if (!item) return;
    onClose();
    router.push(item.href);
  };

  return (
    <Modal
      onClose={onClose}
      title="Jump to"
      hideCloseButton
      initialFocusRef={inputRef}
      width={{ mobile: "92vw", desktop: "480px" }}
      bodyClassName="!p-0"
    >
      <div className="flex items-center gap-2.5 border-b border-osce-border-light px-4">
        <LuSearch className="h-4 w-4 shrink-0 text-b2c-text-muted" aria-hidden />
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setActive(0);
          }}
          onKeyDown={(event) => {
            const { key } = event;
            if (key === "ArrowDown" || key === "ArrowUp") {
              event.preventDefault();
              setActive((index) => moveActive(index, key, matches.length));
            } else if (event.key === "Enter") {
              event.preventDefault();
              go(matches[active]);
            }
          }}
          placeholder="Jump to a section"
          aria-label="Jump to a section"
          className="h-12 min-w-0 flex-1 bg-transparent text-osce-body text-osce-ink-900 outline-none placeholder:text-osce-ink-400"
        />
      </div>
      <ul className="max-h-[50dvh] overflow-y-auto p-1.5" role="listbox" aria-label="Sections">
        {matches.length === 0 ? (
          <li className="px-3 py-6 text-center text-osce-meta text-b2c-text-muted">Nothing matches “{query}”.</li>
        ) : (
          matches.map((item, index) => {
            const Icon = item.icon;
            return (
              <li key={item.key} role="option" aria-selected={index === active}>
                <button
                  type="button"
                  onMouseEnter={() => setActive(index)}
                  onClick={() => go(item)}
                  className={cn(
                    "flex h-10 w-full items-center gap-2.5 rounded-osce-md px-3 text-left text-osce-data text-osce-ink-700",
                    index === active && "bg-osce-navActive text-osce-ink-900",
                  )}
                >
                  {Icon ? <Icon className="h-4 w-4 shrink-0 text-osce-ink-500" /> : null}
                  <span className="min-w-0 truncate">{item.label}</span>
                </button>
              </li>
            );
          })
        )}
      </ul>
    </Modal>
  );
}
