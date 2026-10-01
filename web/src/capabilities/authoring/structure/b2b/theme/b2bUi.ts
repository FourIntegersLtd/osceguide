import { getCardSurfaceClasses } from "@/capabilities/authoring/structure/shared/ui/Card";
import { getInputClassName } from "@/capabilities/authoring/structure/shared/ui/Input";
/** * Shared Tailwind class strings for B2B surfaces (Cursor-inspired tokens in tailwind `b2b-*`). * Primary CTAs: black (`B2BButton variant="commit"`). * Accent / links: blue (`b2b-accent`, `B2BButton variant="primary"`). * Note this is the inverse of B2C, where blue is the ordinary primary and black is reserved for the one committing action on a screen. * Here black is the default and blue the exception — 92 call sites to 8. * * Modals: use `B2BModal` (`capabilities/authoring/structure/b2b/components/ui`) For B2B dialogs (`chrome="titlebar"` For confirms, `chrome="plain"` For * large custom bodies). */ const b2bIconFocus =
  "focus:outline-none focus:ring-2 focus:ring-ink/10 focus:ring-offset-1 rounded-osce-md"; /** Apply on UI portaled to `document.body` So B2B design tokens resolve. */
export const b2bPortalRoot = "b2b-app b2b-portal";
export const b2bIconButton = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md border border-border bg-white text-ink-muted hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonPrimary = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md border border-transparent bg-accent text-white hover:bg-accent-hover disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonDanger = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md border border-danger/30 bg-white text-danger hover:bg-osce-danger-bg disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonSm = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md border border-border bg-white text-ink-muted hover:bg-surface-raised disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonPrimarySm = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md border border-transparent bg-accent text-white hover:bg-accent-hover disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`; /** Anchored dropdown panel (absolute). Prefer {@link b2bDropdownMenuPanel} with `B2BDropdownMenu` Portal positioning. */
export const b2bDropdownMenu = `${b2bPortalRoot} absolute right-0 top-full z-[100] mt-1 min-w-[192px] rounded-osce-lg border border-border bg-white py-1`; /** Fixed/portal menu panel. Positioned via inline styles from `B2BDropdownMenu`. */
export const b2bDropdownMenuPanel = `${b2bPortalRoot} z-[200] min-w-[12rem] rounded-osce-lg border border-border bg-white py-1`;
export const b2bDropdownItem =
  "flex w-full items-center px-3 py-2 text-left text-osce-body font-medium text-ink hover:bg-surface-raised";
export const b2bDropdownItemDanger =
  "flex w-full items-center px-3 py-2 text-left text-osce-body font-medium text-danger hover:bg-osce-danger-bg disabled:opacity-50"; /** Inline text links. Blue accent. */
export const b2bLink =
  "font-medium text-accent hover:text-accent-hover";
export const b2bLinkMuted = "font-medium text-ink-muted hover:text-ink";
export const b2bInputBase = getInputClassName();
export const b2bCard = getCardSurfaceClasses({ themeType: "b2b" }); /** * Design language v3. Cursor-inspired calm surfaces. * See `docs/DESIGN.md`. */ /** Section label above grouped content (e.g. "User API Keys", "Source Control") */
export const b2bEyebrow =
  "text-osce-meta font-medium text-ink-muted"; /** Constrain readable hero / body copy width only (not full-page rails) */
export const b2bProseMeasure = "max-w-2xl";
export const b2bProseMeasureWide = "max-w-3xl";
export const b2bProseMeasureTight = "max-w-xl";
export const b2bHeroTitle =
  "text-osce-heading font-semibold leading-tight tracking-tight text-ink";
export const b2bHeroSubtitle =
  "text-osce-body leading-relaxed text-ink-muted"; /** Outer shell for grouped settings / navigation rows */
export const b2bGroupedShell =
  "min-w-0 max-w-full overflow-hidden rounded-osce-lg border border-border bg-surface"; /** Interactive row inside {@link b2bGroupedShell} (use with Link or button) */
export const b2bGroupedRow =
  "flex min-h-[52px] items-center gap-3 border-b border-border px-4 py-3 transition-colors last:border-b-0 hover:bg-surface-raised";
export const b2bGroupedRowTitle =
  "text-osce-body font-medium leading-snug text-ink";
export const b2bGroupedRowSubtitle =
  "mt-0.5 text-osce-meta leading-snug text-ink-muted"; /** Large focal card (e.g. Primary navigation target) */
export const b2bHeroCtaSurface =
  "block w-full rounded-osce-lg border border-border bg-white p-6 transition-colors hover:bg-surface-raised/40 lg:p-8"; /** Text emphasis for primary inline actions (same as {@link b2bLink}; named for intent) */
export const b2bLinkPrimary =
  b2bLink; /** Standard elevated card. border only, no shadow */
export const b2bCardElevated = b2bCard;
export const b2bCardPlain = `min-w-0 max-w-full ${b2bCard}`;
export const b2bPageTitle =
  "text-osce-title font-semibold text-ink";
export const b2bSectionTitle = "text-osce-body font-semibold text-ink";
/** Segmented control (circuit People/Groups, Team Trainee/Staff, Members vs import). */
export const b2bSegmentedControl =
  "inline-flex flex-wrap items-stretch gap-0 rounded-none border border-border bg-surface p-0 divide-x divide-border";
export const b2bSegmentedTab =
  "inline-flex items-center gap-2 px-3 py-2 text-osce-body font-medium transition-colors";
export const b2bSegmentedTabActive = `${b2bSegmentedTab} bg-surface-raised text-ink`;
export const b2bSegmentedTabInactive = `${b2bSegmentedTab} text-ink-muted hover:bg-surface-raised/60 hover:text-ink`; /** Secondary tabs flush under page header (Team, Partner Users, etc.). */
export const b2bWorkspaceTabStrip =
  "flex flex-wrap items-stretch border-b border-border";
export const b2bWorkspaceTab =
  "inline-flex items-center gap-2 border-b-2 border-transparent px-4 py-2.5 text-osce-body font-medium text-ink-muted transition-colors hover:text-ink -mb-px";
export const b2bWorkspaceTabActive = `${b2bWorkspaceTab} border-b-accent text-accent`;
export const b2bWorkspaceTabInactive = b2bWorkspaceTab;

/** Station review tabs (Transcript / Feedback / GP Lead) — one body scale. */
export const b2bStationReviewBody = "text-osce-body leading-relaxed";
export const b2bStationReviewSectionTitle =
  "text-osce-body font-semibold text-ink";
export const b2bStationReviewMuted = "text-osce-body text-ink-muted";

export const b2bTabPillRoundActive =
  "rounded-osce-md bg-accent px-4 py-2 text-osce-body font-medium text-white";
export const b2bTabPillRoundInactive =
  "rounded-osce-md bg-surface-raised px-4 py-2 text-osce-body font-medium text-ink-muted hover:text-ink";
export const b2bWizardTabActive =
  "border-b-2 border-accent py-2 px-3 text-osce-body font-medium text-accent transition-all whitespace-nowrap md:px-4";
export const b2bWizardTabInactive =
  "border-b-2 border-transparent py-2 px-3 text-osce-body font-medium text-ink-muted transition-all hover:text-ink whitespace-nowrap md:px-4";
export const b2bStepCircleActive =
  "flex h-7 w-7 items-center justify-center rounded-full bg-accent text-osce-caption font-medium text-white";
export const b2bStepCircleInactive =
  "flex h-7 w-7 items-center justify-center rounded-full bg-surface-raised text-osce-body font-medium text-ink-muted";
export const b2bWizardStepCircleActive =
  "flex h-6 w-6 items-center justify-center rounded-full bg-accent text-osce-caption font-medium text-white md:h-8 md:w-8";
export const b2bWizardStepCircleInactive =
  "flex h-6 w-6 items-center justify-center rounded-full bg-surface-raised text-osce-body font-medium text-ink-muted md:h-8 md:w-8 md:text-osce-body";
export const b2bBadgeNumeric =
  "inline-flex h-6 w-6 items-center justify-center rounded-full bg-accent text-osce-caption font-semibold text-white"; /** Sidebar nav link. Active / inactive states */
export const b2bNavLink =
  "flex items-center rounded-osce-md px-3 py-2 text-osce-body font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ink/10";
export const b2bNavLinkActive = `${b2bNavLink} bg-accent-subtle text-accent`;
export const b2bNavLinkInactive = `${b2bNavLink} text-ink-muted hover:bg-surface-raised hover:text-ink`;

export type B2BIconTooltipPlacement = "bottom" | "left" | "top" | "right";

/** Wrapper for icon-only controls that show a hover/focus tooltip chip. */
export const b2bIconTooltipShell = "group relative inline-flex";

/** Chip visuals only — no positioning, so it can be portalled to the body. */
export const b2bIconTooltipChipBase =
  "pointer-events-none z-[200] w-max max-w-[220px] rounded-osce-md border border-border bg-ink px-3 py-1.5 text-osce-caption text-white";

export const b2bIconTooltipChip = `${b2bIconTooltipChipBase} absolute opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100`;

export function b2bIconTooltipPlacement(
  placement: B2BIconTooltipPlacement,
): string {
  switch (placement) {
    case "left":
      return `${b2bIconTooltipChip} right-full top-1/2 mr-2 -translate-y-1/2`;
    case "right":
      return `${b2bIconTooltipChip} left-full top-1/2 ml-2 -translate-y-1/2`;
    case "top":
      return `${b2bIconTooltipChip} bottom-full left-1/2 mb-2 -translate-x-1/2`;
    case "bottom":
    default:
      return `${b2bIconTooltipChip} left-1/2 top-full mt-2 -translate-x-1/2`;
  }
}

export const b2bNavTooltip = `${b2bIconTooltipChip} left-full top-1/2 z-[120] ml-3 -translate-y-1/2 whitespace-nowrap`;
export const b2bNavTooltipArrow =
  "absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-ink";

export const b2bIconButtonGhost = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-osce-md border-0 bg-transparent text-ink-muted hover:bg-surface-raised hover:text-ink disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
/** Borders for the template builder (Start + Structure) and workspace chrome. */
export const b2bBuilderHairlineColor = "border-border";
export const b2bBuilderHairline = `border ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineB = `border-b ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineR = `border-r ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineL = `border-l ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineT = `border-t ${b2bBuilderHairlineColor}`;
export const b2bBuilderDivideY = "divide-y divide-border";
/** Selected card border in the template builder (Start layout cards + Structure field cards). */
export const b2bBuilderCardSelected =
  "border border-accent/30 bg-accent-subtle";
export const b2bBuilderCardSelectedDivider = "border-b border-accent/30";
/** Scrollable builder panels (scrollbars hidden globally in globals.css). */
export const b2bBuilderScrollY = "overflow-y-auto";
/** Workspace-wide aliases (shell + page chrome; same tokens as builder). */
export const b2bWorkspaceHairline = b2bBuilderHairline;
export const b2bWorkspaceHairlineB = b2bBuilderHairlineB;
export const b2bWorkspaceHairlineR = b2bBuilderHairlineR;
export const b2bWorkspaceHairlineL = b2bBuilderHairlineL;
export const b2bWorkspaceHairlineT = b2bBuilderHairlineT;
export const b2bWorkspaceDivideY = b2bBuilderDivideY;
export const b2bWorkspaceCardSelected = b2bBuilderCardSelected;
export const b2bWorkspaceCardSelectedDivider = b2bBuilderCardSelectedDivider;
export const b2bWorkspaceScrollY = b2bBuilderScrollY;
/** Inner padding for page body below flush chrome headers. */
export const b2bPageBody =
  "px-4 py-4 sm:px-6 lg:px-6 lg:py-6"; /** Standard authenticated page column. Prevents horizontal overflow on small screens. */
export const b2bPageColumn = `${b2bPageBody} w-full min-w-0 max-w-full space-y-6 overflow-x-hidden`; /** Flush surface header band (title row + bottom hairline). */
export const b2bPageChromeHeader = `bg-surface ${b2bBuilderHairlineB}`; /** Main scroll region in signed-in workspace shells (org, platform, partner, practice, trainee). */
export const b2bShellMain =
  `${b2bBuilderScrollY} w-full min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden bg-canvas pb-[max(1rem,env(safe-area-inset-bottom,0px))] pt-[calc(4rem+env(safe-area-inset-top,0px))] lg:pb-0 lg:pt-0`; /** Scroll wrapper for wide data tables inside cards. */
export const b2bTableScroll =
  "min-w-0 overflow-x-auto [-webkit-overflow-scrolling:touch]"; /** * Title row + actions: stacks on mobile, side-by-side from `sm`. * Use on custom headers when not using {@link B2BPageHeader}. */
export const b2bStackHeaderRow =
  "flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between"; /** Modal / form footer actions. Stack on narrow viewports. */
export const b2bModalFooterActions =
  "flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row sm:items-center sm:justify-end sm:gap-3"; /** Horizontal tab strip that wraps or scrolls on small screens. */
export const b2bTabStrip =
  `${b2bWorkspaceTabStrip} gap-0 overflow-x-auto [-webkit-overflow-scrolling:touch]`; /** Wizard / step footer: Back + Continue. */
export const b2bWizardFooter =
  "flex flex-col-reverse gap-3 border-t border-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"; /** Ghost outline button (Connect ↗ pattern) */
export const b2bGhostButton =
  "inline-flex items-center gap-1.5 rounded-osce-md border border-border bg-white px-3 py-1.5 text-osce-body font-medium text-ink transition-colors hover:bg-surface-raised focus:outline-none focus:ring-2 focus:ring-ink/10";
/** Solid black CTA. Use instead of raw `bg-accent` For inline `<button>` / `<a>`. */
export const b2bButtonPrimary =
  "inline-flex items-center justify-center gap-2 rounded-osce-md border border-transparent bg-accent px-4 py-2 text-osce-body font-medium text-white transition-colors hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:pointer-events-none disabled:opacity-60";
export const b2bButtonPrimarySm =
  "inline-flex items-center gap-1 rounded-osce-md border border-transparent bg-accent px-2 py-1 text-osce-caption font-medium text-white hover:bg-accent-hover disabled:opacity-50";
export const b2bButtonPrimaryLg =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-osce-lg border border-transparent bg-accent px-6 py-3 text-osce-body font-semibold text-white transition-colors hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:pointer-events-none disabled:opacity-60";
/** Alias of {@link b2bButtonPrimary} for explicit accent intent. */
export const b2bButtonAccent =
  "inline-flex items-center justify-center gap-2 rounded-osce-md border border-transparent bg-accent px-4 py-2 text-osce-body font-medium text-white transition-colors hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:pointer-events-none disabled:opacity-60";

/** Stat / metric tile on dashboards. */
export const b2bStatCard =
  "flex min-w-0 flex-1 flex-col gap-2 rounded-osce-lg border border-border bg-surface p-4 transition-colors hover:border-accent/30 hover:bg-accent-subtle/30";

export const b2bStatCardValue =
  "text-osce-title font-semibold tabular-nums tracking-tight text-ink";

export const b2bStatCardLabel =
  "text-osce-meta font-medium text-ink-muted";

/** Icon chip hues — bg + text pairs for {@link B2BIconChip}. */
export const b2bChipHueClasses = {
  blue: "bg-b2b-chip-blue-bg text-b2b-chip-blue-text",
  violet: "bg-b2b-chip-violet-bg text-b2b-chip-violet-text",
  green: "bg-b2b-chip-green-bg text-b2b-chip-green-text",
  amber: "bg-b2b-chip-amber-bg text-b2b-chip-amber-text",
  rose: "bg-b2b-chip-rose-bg text-b2b-chip-rose-text",
  teal: "bg-b2b-chip-teal-bg text-b2b-chip-teal-text",
} as const;

export type B2BChipHue = keyof typeof b2bChipHueClasses;

export const b2bIconChipBase =
  "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-osce-md";

/** Semantic alert / badge surface tokens (pair with text-* and border-*). */
export const b2bSemanticSuccess =
  "bg-osce-success-bg border-osce-success-border text-osce-success-text";
export const b2bSemanticWarning =
  "bg-osce-warning-bg border-osce-warning-border text-osce-warning-text";
export const b2bSemanticDanger =
  "bg-osce-danger-bg border-osce-danger-border text-osce-danger-text";
export const b2bSemanticInfo =
  "bg-osce-info-bg border-osce-info-border text-osce-info-text";

/** Auth route canvas — classic landing gradient on quiet surfaces (login, change-password). */
export const b2bAuthCanvas =
  "bg-[linear-gradient(180deg,#F5F7FA_0%,#FBFCFD_62%,#FFFFFF_100%)]";
