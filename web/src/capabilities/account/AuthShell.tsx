import type { ReactNode } from "react";
import {
  LuBuilding2,
  LuCircleCheck,
  LuKeyRound,
  LuLoaderCircle,
  LuLock,
  LuMail,
  LuMailCheck,
  LuShieldCheck,
  LuTriangleAlert,
  LuUserPlus,
} from "react-icons/lu";
import { cn } from "@/foundation/ui/cn";
import { Eyebrow, IconTile } from "@/foundation/ui";
import { authCard, authSubtitle, authTitle } from "@/foundation/ui/authTheme";

const ICONS = {
  lock: LuLock,
  shield: LuShieldCheck,
  signup: LuUserPlus,
  key: LuKeyRound,
  mail: LuMail,
  "mail-check": LuMailCheck,
  warning: LuTriangleAlert,
  done: LuCircleCheck,
  building: LuBuilding2,
  working: LuLoaderCircle,
} as const;

export type AuthIconName = keyof typeof ICONS;

type AuthShellProps = {
  title: string;
  subtitle: string;
  eyebrow?: string;
  /** `split` is the card beside the navy panel (`sidePanel`); `card` is the card alone. */
  variant: "split" | "card";
  /** The tile above the title. */
  icon?: AuthIconName;
  /** A card that holds a longer form. */
  wide?: boolean;
  children: ReactNode;
  sidePanel?: ReactNode;
  className?: string;
};

export default function AuthShell({
  title,
  subtitle,
  eyebrow,
  variant,
  icon = "lock",
  wide = false,
  children,
  sidePanel,
  className,
}: AuthShellProps) {
  const Icon = ICONS[icon];
  const card = (
    <section className={cn("min-w-0", authCard)}>
      <header>
        <div className="mb-4 flex items-center gap-3">
          <IconTile>
            <Icon />
          </IconTile>
          {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
        </div>
        <h1 className={authTitle}>{title}</h1>
        <p className={authSubtitle}>{subtitle}</p>
      </header>
      <div className="mt-7 space-y-5">{children}</div>
    </section>
  );

  if (variant === "split") {
    return (
      <div
        className={cn(
          "mx-auto grid w-full max-w-[1120px] flex-1 grid-cols-1 items-stretch gap-10 min-[961px]:grid-cols-[minmax(0,460px)_minmax(0,1fr)]",
          className,
        )}
      >
        {card}
        {sidePanel}
      </div>
    );
  }

  return (
    <div className={cn("mx-auto w-full flex-1", wide ? "max-w-[640px]" : "max-w-[460px]", className)}>{card}</div>
  );
}
