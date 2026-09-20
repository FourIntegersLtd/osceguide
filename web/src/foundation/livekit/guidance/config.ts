/** * Set NEXT_PUBLIC_ENABLE_UI_GUIDANCE=false to disable RPC registration and overlay. * Default: enabled when unset. */
export function isUiGuidanceEnabled(): boolean {
  if (typeof process === "undefined") return false;
  const v = process.env.NEXT_PUBLIC_ENABLE_UI_GUIDANCE;
  if (v === "0" || v === "false" || v === "no") return false;
  return true;
}
