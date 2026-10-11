"use client";

import { HiOutlineMagnifyingGlass, HiOutlineXMark } from "react-icons/hi2";
import { cn, iconSearchInputClassName } from "@/foundation/ui";

/** The one search box on the study screens: type to search, × to clear. */
export function StudySearchBox({
  term,
  onTermChange,
  onClear,
  label,
  placeholder,
}: {
  term: string;
  onTermChange: (term: string) => void;
  onClear: () => void;
  label: string;
  placeholder: string;
}) {
  return (
    <form role="search" onSubmit={(event) => event.preventDefault()} className="relative w-full">
      <HiOutlineMagnifyingGlass
        className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-osce-ink-400"
        aria-hidden
      />
      <input
        type="search"
        placeholder={placeholder}
        value={term}
        onChange={(event) => onTermChange(event.target.value)}
        aria-label={label}
        className={cn(iconSearchInputClassName, "pr-10 text-left")}
      />
      {term !== "" ? (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-osce-ink-400 transition-colors hover:bg-osce-border-light hover:text-osce-ink-600"
          aria-label="Clear search"
        >
          <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : null}
    </form>
  );
}
