import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { BlogIndex } from "@/capabilities/media/BlogIndex";
import { normaliseExamQuery } from "@/capabilities/media/blogs";
import { readFirstBlogPage } from "@/capabilities/media/blogsServer";

// Every `?exam=` tab canonicalises to `/blogs`: they are views of one list.
export const metadata: Metadata = publicPageMetadata({
  path: "/blogs",
  title: "Blogs",
  description: "Guidance and updates for your exam, written by the OSCE Guide study team.",
});

export default async function Page({ searchParams }: { searchParams: Promise<{ exam?: string }> }) {
  const { exam } = await searchParams;
  const examCode = normaliseExamQuery(exam);
  // Keyed by the tab so a tab change starts from that tab's server-read page.
  return <BlogIndex key={examCode ?? ""} examQuery={exam} initialPage={await readFirstBlogPage(examCode)} />;
}
