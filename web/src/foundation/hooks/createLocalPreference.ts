import { useSyncExternalStore } from "react";

/**
 * A device-local preference as an external store, for `useSyncExternalStore`: the server (and the
 * first render) read `fallback`, so there is no hydration mismatch. `encode` returns the string to
 * store, or null to clear the key. Reads and writes are guarded because storage throws in some
 * contexts (private windows, blocked site data); a preference we cannot persist is not worth failing for.
 */
export type LocalPreference<T> = ReturnType<typeof createLocalPreference<T>>;

export function createLocalPreference<T>(options: {
  key: string;
  fallback: T;
  decode: (stored: string) => T;
  encode: (value: T) => string | null;
}) {
  const { key, fallback, decode, encode } = options;
  const listeners = new Set<() => void>();
  return {
    get(): T {
      try {
        const stored = localStorage.getItem(key);
        return stored === null ? fallback : decode(stored);
      } catch {
        return fallback;
      }
    },
    getServer(): T {
      return fallback;
    },
    subscribe(onChange: () => void): () => void {
      listeners.add(onChange);
      return () => {
        listeners.delete(onChange);
      };
    },
    set(value: T): void {
      try {
        const stored = encode(value);
        if (stored === null) localStorage.removeItem(key);
        else localStorage.setItem(key, stored);
      } catch {
        // Not persisted; the in-memory listeners below still update this page.
      }
      listeners.forEach((listener) => listener());
    },
  };
}

/** A device-local on/off switch, stored as "1" when on and cleared when off. */
export function createLocalFlag(key: string) {
  return createLocalPreference<boolean>({
    key,
    fallback: false,
    decode: (stored) => stored === "1",
    encode: (value) => (value ? "1" : null),
  });
}

/** Read a local preference in a component; the server and first render see its fallback. */
export function useLocalPreference<T>(store: LocalPreference<T>): T {
  return useSyncExternalStore(store.subscribe, store.get, store.getServer);
}
