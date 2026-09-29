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
  verifyMfaChallenge,
  startMfaEnrolmentAtSignIn,
  confirmMfaEnrolmentAtSignIn,
  register,
  logout,
  switchWorkspace,
  changePassword,
  requestPasswordReset,
  confirmPasswordReset,
  hasStoredSession,
  installPlatformAuth,
  platformAccessToken,
  peekPlatformAccessToken,
  rememberPlatformSession,
  clearPlatformSession,
  exchangeLegacyToken,
  mintStreamTicket,
  type LegacyProvider,
  type SignInResult,
  type MfaChallenge,
} from "@/foundation/platform-client/auth";
export type { components, paths, operations } from "@/foundation/platform-client/schema";
