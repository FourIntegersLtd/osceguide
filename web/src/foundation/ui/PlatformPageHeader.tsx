import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import { B2CPageHeader } from "@/foundation/ui/B2CPageHeader";

/** Staff console page title — B2C header band and typography. */
export function PlatformPageHeader({
  title,
  description,
  icon,
  actions,
}: {
  title: ReactNode;
  description?: ReactNode;
  icon?: IconType;
  actions?: ReactNode;
}) {
  const heading = typeof title === "string" ? title : String(title);
  const subtitle =
    typeof description === "string"
      ? description
      : description
        ? String(description)
        : undefined;

  return (
    <B2CPageHeader
      title={heading}
      subtitle={subtitle}
      icon={icon}
      action={actions}
      className="mb-0"
    />
  );
}
