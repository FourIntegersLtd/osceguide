import type { ReactNode } from "react";
import { TrainShell } from "@/surfaces";

export default function TrainLayout({ children }: { children: ReactNode }) {
  return <TrainShell>{children}</TrainShell>;
}
