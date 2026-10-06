"use client";

import { useEffect, useState } from "react";

/** False on the server and the first render, true once the client has hydrated. */
export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}
