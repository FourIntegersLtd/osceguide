import type { ReactNode } from "react";
import { TraineeShell } from "@/surfaces";

export default function TraineeLayout({ children }: { children: ReactNode }) {
  return <TraineeShell>{children}</TraineeShell>;
}
