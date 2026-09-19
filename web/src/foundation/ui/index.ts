export { cn } from "@/foundation/ui/cn";

/* Primitives. One per concept: the retiring client had three copies of most
 * of these and they had drifted apart. */
export { Button, getButtonClassName } from "@/foundation/ui/Button";
export type { ButtonProps, ButtonVariant, ButtonSize, ButtonStyleProps } from "@/foundation/ui/Button";
export { ButtonLink } from "@/foundation/ui/ButtonLink";
export { Card, CardHeader, CardTitle, CardContent, CardFooter, getCardSurfaceClasses } from "@/foundation/ui/Card";
export type { CardProps } from "@/foundation/ui/Card";
export { Input, getInputClassName } from "@/foundation/ui/Input";
export type { InputProps, InputSize } from "@/foundation/ui/Input";
export { Badge } from "@/foundation/ui/Badge";
export type { BadgeProps, BadgeVariant, BadgeTone, BadgeSize } from "@/foundation/ui/Badge";
export { TextLink } from "@/foundation/ui/TextLink";
export type { TextLinkProps } from "@/foundation/ui/TextLink";
export { AnchoredTooltip } from "@/foundation/ui/AnchoredTooltip";
export type { AnchoredTooltipPlacement } from "@/foundation/ui/AnchoredTooltip";
export { Alert } from "@/foundation/ui/Alert";
export type { AlertTone } from "@/foundation/ui/Alert";
export { PageHeader } from "@/foundation/ui/PageHeader";
export { EmptyState } from "@/foundation/ui/EmptyState";
export { Spinner } from "@/foundation/ui/Spinner";
export { AsyncBoundary } from "@/foundation/ui/AsyncBoundary";
export type { AsyncBoundaryProps } from "@/foundation/ui/AsyncBoundary";

/* Brand marks and product-specific pills. */
export { default as Logo } from "@/foundation/ui/Logo";
export { AthenaIdentity, ATHENA_IMAGE_SRC } from "@/foundation/ui/AthenaIdentity";
export { B2CBandPill as BandPill, type B2CBandVariant as BandVariant } from "@/foundation/ui/BandPill";

/* Toasts: a provider at the root and a hook anywhere below it. */
export {
  ToastProvider,
  useToastContext,
  useOptionalToastContext,
} from "@/foundation/ui/toast";
export type {
  ToastAction,
  ToastContextValue,
  ToastInput,
  ToastItem,
  ToastTone,
} from "@/foundation/ui/toast";
