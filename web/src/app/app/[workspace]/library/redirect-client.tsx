"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSurface } from "@/capabilities/SurfaceContext";

/** Legacy combined library URL → A to Z list. */
export function LibraryRedirect() {
  const router = useRouter();
  const { hrefFor } = useSurface();

  useEffect(() => {
    router.replace(hrefFor("/summary"));
  }, [hrefFor, router]);

  return null;
}
