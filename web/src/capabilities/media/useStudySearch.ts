"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSearchQuery } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import type { MediaKind } from "@/capabilities/media/api";
import { studyListPath, studySearchPath } from "@/capabilities/media/studyPaths";

/**
 * The study search box: what is typed, and the `?q=` it drives.
 *
 * The URL follows the box 300 ms after typing stops, so results appear as you type
 * and a reload or a shared link keeps the search. `clear` empties both at once.
 */
export function useStudySearch(kind: MediaKind) {
  const router = useRouter();
  const { hrefFor } = useSurface();
  const urlQuery = useSearchParams().get("q")?.trim() ?? "";
  const [term, setTerm] = useState(urlQuery);
  const settled = useSearchQuery(term);
  // The last query this hook put in the URL, so its own arrival does not overwrite newer typing.
  const pushed = useRef(urlQuery);

  useEffect(() => {
    if (urlQuery !== pushed.current) {
      pushed.current = urlQuery;
      setTerm(urlQuery);
    }
  }, [urlQuery]);

  useEffect(() => {
    if (term.trim() !== settled || settled === pushed.current) return;
    pushed.current = settled;
    router.replace(hrefFor(settled === "" ? studyListPath(kind) : studySearchPath(kind, settled)), {
      scroll: false,
    });
  }, [term, settled, kind, hrefFor, router]);

  const clear = useCallback(() => {
    setTerm("");
    pushed.current = "";
    router.replace(hrefFor(studyListPath(kind)), { scroll: false });
  }, [hrefFor, kind, router]);

  return { term, setTerm, urlQuery, clear };
}
