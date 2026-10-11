import type { Metadata } from "next";
import { BlogIndex } from "@/capabilities/media/BlogIndex";

export const metadata: Metadata = {
  title: "Blogs | OSCE Guide",
  description: "Guidance and updates for your exam, written by the OSCE Guide study team.",
};

export default async function Page({ searchParams }: { searchParams: Promise<{ exam?: string }> }) {
  const { exam } = await searchParams;
  return <BlogIndex examCode={exam?.trim().toLowerCase() || null} />;
}
