"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { B2CSkeleton } from "@/foundation/ui";

/** Send legacy `/library/[slug]` hits for tab-native kinds to the study route. */
export function StudyTabRedirect({
  hrefFor,
  path,
}: {
  hrefFor: (path: string) => string;
  path: string;
}) {
  const router = useRouter();

  useEffect(() => {
    router.replace(hrefFor(path));
  }, [hrefFor, path, router]);

  return (
    <div className="w-full text-left">
      <B2CSkeleton.Card lines={8} className="min-h-[320px]" />
    </div>
  );
}
