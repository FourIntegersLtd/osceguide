"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  hasStoredSession,
  forgetAccessToken,
  installPlatformAuth,
  logout as apiLogout,
  PlatformError,
  platformRequest,
  setUnauthorizedHandler,
  switchWorkspace as apiSwitchWorkspace,
} from "@/foundation/platform-client";
import { usePathname } from "next/navigation";
import { signedOutDestination, type SignedOut } from "@/foundation/session/loginHref";
import { sessionLoads } from "@/foundation/session/sessionLoads";
import { rememberSessionUser } from "@/foundation/session/sessionUser";
import type { PlatformCapabilities, PlatformUser, Session, SessionState, SessionStatus } from "@/foundation/session/types";

const SessionContext = createContext<SessionState | null>(null);

/** How long to wait before asking `/me` again after a failure that was not a 401. */
const RETRY_FIRST_MS = 1_000;
const RETRY_MAX_MS = 30_000;

// Installed at module scope so the very first request already carries a token;
// doing it in an effect races the fetches a page fires on mount.
let installed = false;
function ensureAuthInstalled() {
  if (installed) return;
  installed = true;
  installPlatformAuth();
}

/**
 * Resolves who is signed in, once, for the whole app.
 *
 * `/me` and `/me/capabilities` are fetched together rather than by whichever
 * screen happens to need one: two sources of truth for "may I" is how a nav
 * item and the route it leads to came to disagree in the old client.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  ensureAuthInstalled();
  const [session, setSession] = useState<Session | null>(null);
  /*
   * Always "loading" to begin with, on the server and on the first client
   * paint alike.
   *
   * Seeding this from `hasStoredSession()` read `localStorage`, which does not
   * exist during a server render: the server decided "anonymous, resolved" and
   * the browser decided "loading", so every gated screen hydrated against a
   * different tree and React threw the whole thing away and re-rendered. The
   * answer is not knowable before mount, so nothing pretends to know it.
   */
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [sessionExpired, setSessionExpired] = useState(false);
  const [signedOut, setSignedOut] = useState<SignedOut | null>(null);
  const pathname = usePathname() ?? "/";
  // A sign-out's destination is spent once the person leaves the page they signed out from
  // (adjusted during render, React's pattern for state that follows a changed value).
  if (signedOut && signedOut.from !== pathname) setSignedOut(null);
  const [ready, setReady] = useState(false);
  // Failures in a row that were not a 401; each one schedules another try.
  const [failedAttempts, setFailedAttempts] = useState(0);

  /** Answers the session it loaded, or null when there is none or it could not be asked. */
  const load = useCallback(async (): Promise<Session | null> => {
    if (!hasStoredSession()) {
      setSession(null);
      setSessionExpired(false);
      setStatus("anonymous");
      setReady(true);
      return null;
    }
    try {
      const [user, capabilities] = await Promise.all([
        platformRequest<PlatformUser>("/api/v1/me"),
        platformRequest<PlatformCapabilities>("/api/v1/me/capabilities"),
      ]);
      const loaded = { user, capabilities };
      setSession(loaded);
      rememberSessionUser(user.id);
      setSessionExpired(false);
      setSignedOut(null);
      setStatus("authenticated");
      setFailedAttempts(0);
      return loaded;
    } catch (cause) {
      // Only a 401 is an answer about who this is: the stored pair was
      // presented and refused. Anything else (a 500, a proxy reset, no network)
      // says nothing about the person, so whatever was known is kept and the
      // question is asked again. Treating every failure as a sign-out sent
      // people to /login in the middle of a live peer session.
      if (cause instanceof PlatformError && cause.status === 401) {
        setSession(null);
        setSessionExpired(true);
        setStatus("anonymous");
      } else {
        setFailedAttempts((count) => count + 1);
      }
      return null;
    } finally {
      setReady(true);
    }
  }, []);

  // Background re-checks share one load; `refresh` (called after a sign-in) waits out a load that
  // started with the old tokens and answers from a new one. See `sessionLoads`.
  const [loads] = useState(() => sessionLoads(load));
  const recheck = loads.join;
  const refresh = loads.after;

  useEffect(() => {
    void recheck();
  }, [recheck]);

  // A 401 on any later request means the token was refused (the session was revoked, or its chain
  // ended). Ask who this is again rather than leaving every screen to show its own error: a real
  // sign-out lands on the sign-in page, a token that only expired is replaced and nothing shows.
  useEffect(() => {
    setUnauthorizedHandler(() => {
      forgetAccessToken();
      void recheck();
    });
    return () => setUnauthorizedHandler(null);
  }, [recheck]);

  // After a failure that was not a 401, ask again: 1s, 2s, 4s … capped at 30s.
  useEffect(() => {
    if (failedAttempts === 0) return;
    const delay = Math.min(RETRY_FIRST_MS * 2 ** (failedAttempts - 1), RETRY_MAX_MS);
    const timer = setTimeout(() => void recheck(), delay);
    return () => clearTimeout(timer);
  }, [failedAttempts, recheck]);

  const signOut = useCallback(
    async (to = "/login") => {
      await apiLogout();
      rememberSessionUser(null);
      setSession(null);
      setSessionExpired(false);
      setSignedOut({ to, from: pathname });
      setStatus("anonymous");
    },
    [pathname],
  );

  const selectWorkspace = useCallback(
    async (orgSlug: string | null) => {
      await apiSwitchWorkspace(orgSlug);
      // The new token carries the new active membership, so everything derived
      // from it has to be re-read rather than patched locally.
      await load();
    },
    [load],
  );

  // Only while nothing is known: a signed-in person whose re-check fails keeps
  // what was known, as above.
  const unavailable = status === "loading" && failedAttempts > 0;

  const signedOutTo = signedOutDestination(signedOut, pathname);

  const value = useMemo<SessionState>(
    () => ({ status, session, ready, sessionExpired, signedOutTo, unavailable, refresh, signOut, selectWorkspace }),
    [status, session, ready, sessionExpired, signedOutTo, unavailable, refresh, signOut, selectWorkspace],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within a SessionProvider");
  return ctx;
}
