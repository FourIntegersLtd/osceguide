export { SessionProvider, useSession } from "@/foundation/session/SessionProvider";
export { useCurrentExam, type CurrentExam } from "@/foundation/session/useCurrentExam";
export { RequireSession, RequireCapability } from "@/foundation/session/guards";
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
