import type { Metadata } from "next";
import { BlogArticle } from "@/capabilities/media/BlogArticle";

export const metadata: Metadata = { title: "Blogs | OSCE Guide" };

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <BlogArticle slug={slug} />;
}
