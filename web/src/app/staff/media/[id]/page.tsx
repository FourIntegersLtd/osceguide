"use client";

import { useRouter } from "next/navigation";
import { use } from "react";
import { MediaDetailScreen } from "@/capabilities/staff-media/MediaDetailScreen";
import { staffMediaListPath } from "@/capabilities/staff-media/paths";

export default function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  return (
    <MediaDetailScreen
      itemId={id}
      onBack={(kind) =>
        router.push(kind ? staffMediaListPath(kind) : "/staff/media")
      }
    />
  );
}
