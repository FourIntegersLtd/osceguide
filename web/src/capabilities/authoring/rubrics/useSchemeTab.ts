"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { parseTab } from "@/capabilities/authoring/rubrics/schemeTabs";
import type { SchemeTabId } from "@/capabilities/authoring/rubrics/schemeModel";

/** The tab and the "published" notice, both kept in the address so a link or a reload lands on the same screen. */
export function useSchemeTab(): { tab: SchemeTabId; published: boolean; go: (tab: SchemeTabId) => void; markPublished: () => void } {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const write = (key: string, value: string) => {
    const query = new URLSearchParams(params.toString());
    query.set(key, value);
    router.replace(`${pathname}?${query.toString()}`, { scroll: false });
  };
  return {
    tab: parseTab(params.get("tab")),
    published: params.get("published") === "1",
    go: (tab) => write("tab", tab),
    markPublished: () => write("published", "1"),
  };
}
