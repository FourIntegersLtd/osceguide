import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";
import { boardInput } from "@/foundation/ui/boardKit";

/**
 * The board's native form controls (14px, 44px tall), for the screens matched to docs/institution-overhaul/boards.
 * The kit's Select, Textarea and Checkbox are the 16px app controls; these are the board's own, kept here so the
 * screens stay free of raw elements (consoleDesign.test.ts).
 */
export function BoardSelect({ className = "", ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={`${boardInput} ${className}`} />;
}

export function BoardTextarea({ className = "", ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={`${boardInput} resize-y py-2.5 ${className}`} />;
}

export function BoardCheckbox({ label, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, "type"> & { label: ReactNode }) {
  return (
    <label className="flex min-h-8 items-start gap-2.5 text-assess-label text-ink">
      <input type="checkbox" {...props} className="mt-0.5 h-[18px] w-[18px] accent-accent" />
      {label}
    </label>
  );
}
