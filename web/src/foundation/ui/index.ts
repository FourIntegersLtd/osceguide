export { cn } from "@/foundation/ui/cn";

/* Primitives. One per concept: the retiring client had three copies of most
 * of these and they had drifted apart. */
export { Button, getButtonClassName } from "@/foundation/ui/Button";
export type { ButtonProps, ButtonVariant, ButtonSize, ButtonStyleProps } from "@/foundation/ui/Button";
export { ButtonLink } from "@/foundation/ui/ButtonLink";
export { Card, CardHeader, CardTitle, CardContent, CardFooter, cardScrollBody, getCardSurfaceClasses } from "@/foundation/ui/Card";
export type { CardProps } from "@/foundation/ui/Card";
export { Input, getInputClassName } from "@/foundation/ui/Input";
export { Select } from "@/foundation/ui/Select";
export { Textarea } from "@/foundation/ui/Textarea";
export { Checkbox } from "@/foundation/ui/Checkbox";
export { SectionSearchField } from "@/foundation/ui/SectionSearchField";
export { iconSearchInputClassName } from "@/foundation/ui/inputStyles";
export type { InputProps, InputSize } from "@/foundation/ui/Input";
export { Badge } from "@/foundation/ui/Badge";
export type { BadgeProps, BadgeVariant, BadgeTone, BadgeSize } from "@/foundation/ui/Badge";
export { TextLink } from "@/foundation/ui/TextLink";
export type { TextLinkProps } from "@/foundation/ui/TextLink";
export { AnchoredTooltip } from "@/foundation/ui/AnchoredTooltip";
export type { AnchoredTooltipPlacement } from "@/foundation/ui/AnchoredTooltip";
export { StepRail, NextStepBar, StepGuide } from "@/foundation/ui/StepRail";
export type { RailStep } from "@/foundation/ui/StepRail";
export { Alert } from "@/foundation/ui/Alert";
export type { AlertTone } from "@/foundation/ui/Alert";
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

/* ------------------------------------------------------------------------
 * The retiring client's own primitives, brought across with the screens that
 * use them. They name the product palette in `osceTokens.css` directly, which
 * is why a ported screen still looks exactly as it does today. New code should
 * reach for the semantic primitives above.
 * --------------------------------------------------------------------- */
export { B2CEmptyState } from "@/foundation/ui/B2CEmptyState";
export { B2CErrorState, B2CInlineError } from "@/foundation/ui/B2CErrorState";
export { B2CFormField } from "@/foundation/ui/B2CFormField";
export { B2CGroupedSection, B2CGroupedRow, B2CGroupedRowLink } from "@/foundation/ui/B2CGroupedList";
export { B2CBandBar } from "@/foundation/ui/B2CBandBar";
export { B2CHero } from "@/foundation/ui/B2CHero";
export { B2CMonoEyebrow } from "@/foundation/ui/B2CMonoEyebrow";
export { B2CPageHeader, type B2CPageHeaderProps } from "@/foundation/ui/B2CPageHeader";
export {
  B2CPanelCard,
  B2CPanelCardHeaderIcon,
  B2CPanelCardHeader,
  B2CPanelCardBody,
  B2CPanelCardFooter,
} from "@/foundation/ui/B2CPanelCard";
export {
  B2CSectionIconBadge,
  type B2CSectionIconTone,
  type B2CSectionIconBadgeSize,
} from "@/foundation/ui/B2CSectionIconBadge";
export {
  B2CSegmentedTabs,
  type B2CSegmentedTabItem,
  type B2CSegmentedTabsProps,
} from "@/foundation/ui/B2CSegmentedTabs";
export { QuietCard } from "@/foundation/ui/QuietCard";
export { B2CSkeleton } from "@/foundation/ui/B2CSkeleton";
export { default as Back } from "@/foundation/ui/Back";
export { default as Confetti } from "@/foundation/ui/Confetti";
export { default as LoadingSpinner } from "@/foundation/ui/LoadingSpinner";
export { default as MarkdownRenderer } from "@/foundation/ui/MarkdownRenderer";
export { default as Pagination } from "@/foundation/ui/Pagination";
export { default as PhotoUpload, type PhotoUploadResult } from "@/foundation/ui/PhotoUpload";
export { default as StationCompletionProgressBar } from "@/foundation/ui/ProgressBar";
export { default as Timer, FINAL_COUNTDOWN_SECONDS } from "@/foundation/ui/Timer";
export { default as UnauthorizedAccess } from "@/foundation/ui/UnauthorizedAccess";
export { default as DeepgramLogo } from "@/foundation/ui/DeepgramLogo";
export { linkifyOptions } from "@/foundation/ui/Linkify";

/* Toasts: the provider goes at the root, `useToast` anywhere below it. */
export { B2CToastProvider as ToastHost } from "@/foundation/ui/B2CToastProvider";
export { B2CToastViewport } from "@/foundation/ui/B2CToastViewport";
export { B2CToastCard } from "@/foundation/ui/B2CToastCard";
export * from "@/foundation/ui/AboutInfo";

/* Modals. One overlay, one focus trap, one place Escape is handled. */
export { default as Modal } from "@/foundation/ui/Modal";
export { default as ConfirmModal, type ConfirmModalProps } from "@/foundation/ui/ConfirmModal";
export { default as LeaveConfirmModal } from "@/foundation/ui/LeaveConfirmModal";
export { default as CookiesConsentModal } from "@/foundation/ui/CookiesConsentModal";
export * from "@/foundation/ui/ModalContent";
export * from "@/foundation/ui/ModalSection";

/* The product's class-name vocabularies, for ported screens. */
export * as productTokens from "@/foundation/ui/productTokens";
export * as b2bTokens from "@/foundation/ui/b2bTokens";

/* Platform chrome — generic staff-console layout primitives. */
export { PlatformPageHeader } from "@/foundation/ui/PlatformPageHeader";
export { PlatformTabbedScreen } from "@/foundation/ui/PlatformTabbedScreen";
export {
  PlatformFilterBar,
  PlatformFilterDivider,
  PlatformFilterSelect,
  PlatformFilterSearch,
} from "@/foundation/ui/PlatformFilterBar";
export {
  Panel,
  FoldSection,
  RowList,
  Row,
  RowLink,
  LoadMore,
  StatGrid,
  StatTile,
  EmptyPanel,
  DetailLayout,
  ActionRail,
  FactList,
} from "@/foundation/ui/PlatformConsole";
export {
  platformStaffPanel,
  platformStaffHairlineB,
  platformStaffHairlineT,
  platformStaffFilterSection,
  platformStaffFilterBox,
  platformStaffFilterDivider,
} from "@/foundation/ui/platformStaffChrome";
