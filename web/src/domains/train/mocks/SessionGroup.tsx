import type { ReactNode } from "react";
import { productTokens } from "@/foundation/ui";

/**
 * A labelled group of session cards (canvas `train-sessions`): the label,
 * "Current subscription · 4", sits over the grid.
 */
export function SessionGroup({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h2 className={`px-1 pb-2 ${productTokens.b2cMonoEyebrow}`}>{title}</h2>
      {children}
    </section>
  );
}
