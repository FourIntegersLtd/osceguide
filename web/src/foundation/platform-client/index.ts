export { platformRequest, platformApiUrl, setPlatformTokenSource, type RequestOptions } from "@/foundation/platform-client/client";
export {
  PlatformError,
  PlatformTransportError,
  isPlatformError,
  hasCode,
  type PlatformErrorCode,
  type PlatformErrorBody,
} from "@/foundation/platform-client/errors";
export {
  login,
  register,
  logout,
  switchWorkspace,
  changePassword,
  requestPasswordReset,
  hasStoredSession,
  installPlatformAuth,
  platformAccessToken,
  peekPlatformAccessToken,
  rememberPlatformSession,
  clearPlatformSession,
  exchangeLegacyToken,
  type LegacyProvider,
} from "@/foundation/platform-client/auth";
export type { components, paths, operations } from "@/foundation/platform-client/schema";
