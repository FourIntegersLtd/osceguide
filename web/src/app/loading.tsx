import { Spinner } from "@/foundation/ui";

export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner label="Loading" size="lg" className="text-ink-subtle" />
    </div>
  );
}
