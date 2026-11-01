export { SessionProvider, useSession } from "@/foundation/session/SessionProvider";
export { useCurrentExam, type CurrentExam, type ExamSettings } from "@/foundation/session/useCurrentExam";
export {
  helpModeChoice,
  offersPatientPractice,
  showsMarkingTips,
  hasStationSubtypes,
} from "@/foundation/session/examSettingsRules";
export { RequireExam } from "@/foundation/session/RequireExam";
export { classifyExam, type ExamState } from "@/foundation/session/examCode";
export { RequireSession, RequireCapability, RequireAnonymous } from "@/foundation/session/guards";
export { PERMISSIONS, type Permission } from "@/foundation/session/permissions";
export {
  can,
  isPlatformAdmin,
  activeMembership,
  type Session,
  type SessionState,
  type SessionStatus,
  type PlatformUser,
  type PlatformMembership,
  type PlatformCapabilities,
} from "@/foundation/session/types";
export { sanitizeReturnTo, isPublicPath } from "@/foundation/session/returnTo";
