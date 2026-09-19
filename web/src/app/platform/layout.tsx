import type { ReactNode } from "react";
import { RequireCapability } from "@/foundation/session";
import { PlatformShell } from "@/surfaces";

export default function PlatformLayout({ children }: { children: ReactNode }) {
  return (
    <PlatformShell>
      <RequireCapability permission="administer_platform">{children}</RequireCapability>
    </PlatformShell>
  );
}
