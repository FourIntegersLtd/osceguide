export { SessionProvider, useSession } from "@/foundation/session/SessionProvider";
export { RequireSession, RequireCapability } from "@/foundation/session/guards";
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
