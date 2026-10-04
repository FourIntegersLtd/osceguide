import { useSyncExternalStore } from "react";

/**
 * Whether the page is running as the installed app rather than in a browser tab.
 *
 * iOS reports a home-screen launch through Safari's own `navigator.standalone`;
 * everything else answers the `display-mode` media query.
 */
export function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia(
      "(display-mode: standalone), (display-mode: fullscreen), (display-mode: minimal-ui)",
    ).matches || (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

// How a page is displayed is fixed for its lifetime, so there is nothing to subscribe to.
const subscribe = () => () => {};

/** `isStandaloneDisplay` for render: false on the server and during hydration. */
export function useStandaloneDisplay(): boolean {
  return useSyncExternalStore(subscribe, isStandaloneDisplay, () => false);
}
