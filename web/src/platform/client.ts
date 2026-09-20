/**
 * Shim for `@/b2b` modules still importing `@/platform/client` from the
 * retiring frontend tree. Re-exports the unified client so auth shares one
 * `setPlatformTokenSource` with `SessionProvider`.
 */
export {
  platformApiUrl,
  platformRequest,
  setPlatformTokenSource,
  type RequestOptions,
} from "@/foundation/platform-client/client";
