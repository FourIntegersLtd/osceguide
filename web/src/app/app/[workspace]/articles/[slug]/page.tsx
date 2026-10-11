import { Capability } from "@/app/app/[workspace]/capability";
import { MediaItemView } from "@/capabilities/media";

export default async function Page({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <Capability id="study-articles">
      <MediaItemView slug={slug} />
    </Capability>
  );
}
