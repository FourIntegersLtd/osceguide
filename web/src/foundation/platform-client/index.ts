export {
  platformRequest,
  platformDownload,
  platformStream,
  saveBlob,
  platformApiUrl,
  setPlatformTokenSource,
  type RequestOptions,
  type PlatformDownload,
} from "@/foundation/platform-client/client";
export type { SseFrame } from "@/foundation/platform-client/sse";
export {
  PlatformError,
  PlatformTransportError,
  isPlatformError,
  hasCode,
  validationFields,
  type PlatformErrorCode,
  type PlatformErrorBody,
} from "@/foundation/platform-client/errors";
export { describeRefusal, isNotEntitled } from "@/foundation/platform-client/refusal";
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
