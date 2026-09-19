import { MediaItemView } from "@/capabilities/media";

export default async function OrgMediaPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <MediaItemView slug={slug} />;
}
