import { cn } from "@/foundation/ui/cn";
import { b2cMonoEyebrow } from "@/foundation/ui/productTokens";

type B2CMonoEyebrowProps = {
  children: React.ReactNode;
  className?: string;
};

export function B2CMonoEyebrow({ children, className }: B2CMonoEyebrowProps) {
  return <p className={cn(b2cMonoEyebrow, className)}>{children}</p>;
}
