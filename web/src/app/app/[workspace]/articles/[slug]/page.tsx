import { redirect } from "next/navigation";

/** Articles are the public /blogs pages now. */
export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  redirect(`/blogs/${encodeURIComponent(slug)}`);
}
