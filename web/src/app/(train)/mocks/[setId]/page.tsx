import { MockDetail } from "@/domains/train";

export default async function MockPage({ params }: { params: Promise<{ setId: string }> }) {
  const { setId } = await params;
  return <MockDetail setId={setId} />;
}
