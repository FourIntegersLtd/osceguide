import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import {
  authCard,
  authEyebrowPill,
  authSubtitle,
  authTitle,
} from "@/foundation/ui/authTheme";

type AuthShellProps = {
  title: string;
  subtitle: string;
  eyebrow?: string;
  variant: "split" | "card";
  children: ReactNode;
  sidePanel?: ReactNode;
  className?: string;
};

export default function AuthShell({
  title,
  subtitle,
  eyebrow,
  variant,
  children,
  sidePanel,
  className,
}: AuthShellProps) {
  if (variant === "split") {
    return (
      <div
        className={cn(
          "grid h-full min-h-0 w-full flex-1 grid-cols-1 lg:grid-cols-2",
          className,
        )}
      >
        <div className="flex min-h-0 flex-col justify-center overflow-y-auto py-6 lg:py-8">
          <div className="mx-auto w-full max-w-md space-y-8 px-1 sm:space-y-10">
            <header className="space-y-3 text-center lg:text-left">
              {eyebrow ? (
                <span className={authEyebrowPill}>{eyebrow}</span>
              ) : null}
              <h1 className={authTitle}>{title}</h1>
              <p className={authSubtitle}>{subtitle}</p>
            </header>
            {children}
          </div>
        </div>
        {sidePanel}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex h-full min-h-0 flex-1 items-center justify-center overflow-y-auto py-6",
        className,
      )}
    >
      <div className={cn("w-full max-w-[420px] space-y-8", authCard)}>
        <header className="space-y-2 text-center">
          {eyebrow ? (
            <span className={cn(authEyebrowPill, "mx-auto")}>{eyebrow}</span>
          ) : null}
          <h1 className={authTitle}>{title}</h1>
          <p className={authSubtitle}>{subtitle}</p>
        </header>
        {children}
      </div>
    </div>
  );
}
