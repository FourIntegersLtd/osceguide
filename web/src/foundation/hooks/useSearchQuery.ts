"use client";

import { useEffect, useState } from "react";

/** How long typing must pause before the search is sent, in milliseconds. */
const TYPING_PAUSE_MS = 300;

/**
 * The text of a search box, ready to send to the server.
 *
 * Pass in what the person has typed so far. The value returned is that text
 * with the spaces trimmed from both ends, and it only changes once they have
 * stopped typing for a moment. A screen puts the returned value in its loader's
 * dependencies, so one request is sent per pause rather than one per key.
 *
 * Searching itself is always done by the server; this only decides when to ask.
 */
export function useSearchQuery(typedText: string): string {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(typedText.trim()), TYPING_PAUSE_MS);
    return () => window.clearTimeout(timer);
  }, [typedText]);

  return query;
}
