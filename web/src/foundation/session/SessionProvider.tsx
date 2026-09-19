"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  hasStoredSession,
  installPlatformAuth,
  logout as apiLogout,
  platformRequest,
  switchWorkspace as apiSwitchWorkspace,
} from "@/foundation/platform-client";
import type { PlatformCapabilities, PlatformUser, Session, SessionState, SessionStatus } from "@/foundation/session/types";

const SessionContext = createContext<SessionState | null>(null);

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
  const [status, setStatus] = useState<SessionStatus>(() =>
    hasStoredSession() ? "loading" : "anonymous",
  );
  const [ready, setReady] = useState(() => !hasStoredSession());
  const inFlight = useRef<Promise<void> | null>(null);

  const load = useCallback(async () => {
    if (!hasStoredSession()) {
      setSession(null);
      setStatus("anonymous");
      setReady(true);
      return;
    }
    try {
      const [user, capabilities] = await Promise.all([
        platformRequest<PlatformUser>("/api/v1/me"),
        platformRequest<PlatformCapabilities>("/api/v1/me/capabilities"),
      ]);
      setSession({ user, capabilities });
      setStatus("authenticated");
    } catch {
      // A refused /me means the stored pair is spent. Treating it as anonymous
      // sends the person to sign in rather than leaving a half-built shell.
      setSession(null);
      setStatus("anonymous");
    } finally {
      setReady(true);
    }
  }, []);

  const refresh = useCallback(async () => {
    // Concurrent callers share one resolution; several screens ask at once
    // after a sign-in and three /me calls answer the same question.
    inFlight.current ??= load().finally(() => {
      inFlight.current = null;
    });
    return inFlight.current;
  }, [load]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    await apiLogout();
    setSession(null);
    setStatus("anonymous");
  }, []);

  const selectWorkspace = useCallback(
    async (orgSlug: string) => {
      await apiSwitchWorkspace(orgSlug);
      // The new token carries the new active membership, so everything derived
      // from it has to be re-read rather than patched locally.
      await load();
    },
    [load],
  );

  const value = useMemo<SessionState>(
    () => ({ status, session, ready, refresh, signOut, selectWorkspace }),
    [status, session, ready, refresh, signOut, selectWorkspace],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within a SessionProvider");
  return ctx;
}
