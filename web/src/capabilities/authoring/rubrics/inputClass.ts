import { cn, getInputClassName } from "@/foundation/ui";

/** A small text or number input in the builder's blocks. */
export const inputClass = cn(getInputClassName({ size: "sm" }), "min-w-0");
