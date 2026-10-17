"use client";

import { Alert, Button } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import { describeRefusal } from "@/capabilities/stations";

/** The panel shown when a station's attempt could not be created. */
export function StartFailureAlert({
  cause,
  onRetry,
  onBack,
}: {
  cause: unknown;
  onRetry: () => void;
  onBack: () => void;
}) {
  const { surface } = useSurface();
  return (
    <Alert tone="danger" title="This station could not be started">
      <p>{describeRefusal(cause, "We could not start this station. Please try again.", surface)}</p>
      <div className="mt-3 flex gap-2">
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
        <Button variant="secondary" size="sm" onClick={onBack}>
          Go back
        </Button>
      </div>
    </Alert>
  );
}
