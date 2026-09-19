/*
 * The institution workspace's class-name vocabulary, from the retiring
 * client's `b2b/theme/b2bUi.ts`.
 *
 * Sits beside `productTokens.ts` (the consumer set) rather than merged into
 * it, because the two arms genuinely read the same palette differently: black
 * is B2C's one committing action and B2B's ordinary primary, blue is B2C's
 * primary and B2B's accent. Same colours, opposite frequency. Merging them
 * would mean picking one arm's reading and quietly restyling the other.
 */
import { getCardSurfaceClasses } from "@/foundation/ui";
import { getInputClassName } from "@/foundation/ui";
/** * Shared Tailwind class strings for B2B surfaces (Cursor-inspired tokens in tailwind `b2b-*`). * Primary CTAs: black (`B2BButton variant="commit"`). * Accent / links: blue (`b2b-accent`, `B2BButton variant="primary"`). * Note this is the inverse of B2C, where blue is the ordinary primary and black is reserved for the one committing action on a screen. * Here black is the default and blue the exception — 92 call sites to 8. * * Modals: use `@/b2b/components/ui/B2BModal` For B2B dialogs (`chrome="titlebar"` For confirms, `chrome="plain"` For * large custom bodies). Do not import the legacy B2C `Modal` Under `src/b2b`. * * Session data: for the common session + trainees + stations + staff bundle, see `b2bPrefetchSessionBundle` In * `@/b2b/lib/api/b2bSessionBundle`. */ const b2bIconFocus =
  "focus:outline-none focus:ring-2 focus:ring-b2b-headline/10 focus:ring-offset-1 rounded-md"; /** Apply on UI portaled to `document.body` So B2B design tokens resolve. */
export const b2bPortalRoot = "b2b-app b2b-portal";
export const b2bIconButton = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-b2b-border bg-white text-b2b-graphite hover:bg-b2b-cream disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonPrimary = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-transparent bg-b2b-accent text-white hover:bg-b2b-accent-hover disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonDanger = `inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-b2b-danger/30 bg-white text-b2b-danger hover:bg-b2b-danger-bg disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonSm = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-b2b-border bg-white text-b2b-graphite hover:bg-b2b-cream disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
export const b2bIconButtonPrimarySm = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-transparent bg-b2b-accent text-white hover:bg-b2b-accent-hover disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`; /** Anchored dropdown panel (absolute). Prefer {@link b2bDropdownMenuPanel} with `B2BDropdownMenu` Portal positioning. */
export const b2bDropdownMenu = `${b2bPortalRoot} absolute right-0 top-full z-[100] mt-1 min-w-[192px] rounded-lg border border-b2b-border bg-white py-1`; /** Fixed/portal menu panel. Positioned via inline styles from `B2BDropdownMenu`. */
export const b2bDropdownMenuPanel = `${b2bPortalRoot} z-[200] min-w-[12rem] rounded-lg border border-b2b-border bg-white py-1`;
export const b2bDropdownItem =
  "flex w-full items-center px-3 py-2 text-left text-osce-body font-medium text-b2b-headline hover:bg-b2b-cream";
export const b2bDropdownItemDanger =
  "flex w-full items-center px-3 py-2 text-left text-osce-body font-medium text-b2b-danger hover:bg-b2b-danger-bg disabled:opacity-50"; /** Inline text links. Blue accent. */
export const b2bLink =
  "font-medium text-b2b-accent hover:text-b2b-accent-hover";
export const b2bLinkMuted = "font-medium text-b2b-mid hover:text-b2b-headline";
/** @deprecated Focus styling belongs to the shared control. */
export const b2bInputFocus =
  "focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle";
export const b2bInputBase = getInputClassName();
export const b2bCard = getCardSurfaceClasses({ themeType: "b2b" }); /** * Design language v3. Cursor-inspired calm surfaces. * See repo `.cursor/rules/b2b-design-language.mdc`. */ /** Section label above grouped content (e.g. "User API Keys", "Source Control") */
export const b2bEyebrow =
  "text-osce-meta font-medium text-b2b-mid"; /** Constrain readable hero / body copy width only (not full-page rails) */
export const b2bProseMeasure = "max-w-2xl";
export const b2bProseMeasureWide = "max-w-3xl";
export const b2bProseMeasureTight = "max-w-xl";
export const b2bHeroTitle =
  "text-osce-heading font-semibold leading-tight tracking-tight text-b2b-headline";
export const b2bHeroSubtitle =
  "text-osce-body leading-relaxed text-b2b-mid"; /** Outer shell for grouped settings / navigation rows */
export const b2bGroupedShell =
  "min-w-0 max-w-full overflow-hidden rounded-lg border border-b2b-border bg-b2b-surface"; /** Interactive row inside {@link b2bGroupedShell} (use with Link or button) */
export const b2bGroupedRow =
  "flex min-h-[52px] items-center gap-3 border-b border-b2b-border px-4 py-3 transition-colors last:border-b-0 hover:bg-b2b-cream";
export const b2bGroupedRowTitle =
  "text-osce-body font-medium leading-snug text-b2b-headline";
export const b2bGroupedRowSubtitle =
  "mt-0.5 text-osce-meta leading-snug text-b2b-mid"; /** Large focal card (e.g. Primary navigation target) */
export const b2bHeroCtaSurface =
  "block w-full rounded-lg border border-b2b-border bg-white p-6 transition-colors hover:bg-b2b-cream/40 lg:p-8"; /** Text emphasis for primary inline actions (same as {@link b2bLink}; named for intent) */
export const b2bLinkPrimary =
  b2bLink; /** Standard elevated card. border only, no shadow */
export const b2bCardElevated = b2bCard;
export const b2bCardPlain = `min-w-0 max-w-full ${b2bCard}`;
export const b2bPageTitle =
  "text-osce-title font-semibold text-b2b-headline";
export const b2bSectionTitle = "text-osce-body font-semibold text-b2b-headline";
/** Segmented control (circuit People/Groups, Team Trainee/Staff, Members vs import). */
export const b2bSegmentedControl =
  "inline-flex flex-wrap items-stretch gap-0 rounded-none border border-b2b-border bg-b2b-surface p-0 divide-x divide-b2b-border";
export const b2bSegmentedTab =
  "inline-flex items-center gap-2 px-3 py-2 text-osce-body font-medium transition-colors";
export const b2bSegmentedTabActive = `${b2bSegmentedTab} bg-b2b-cream text-b2b-headline`;
export const b2bSegmentedTabInactive = `${b2bSegmentedTab} text-b2b-mid hover:bg-b2b-cream/60 hover:text-b2b-headline`; /** Secondary tabs flush under page header (Team, Partner Users, etc.). */
export const b2bWorkspaceTabStrip =
  "flex flex-wrap items-stretch border-b border-b2b-border";
export const b2bWorkspaceTab =
  "inline-flex items-center gap-2 border-b-2 border-transparent px-4 py-2.5 text-osce-body font-medium text-b2b-mid transition-colors hover:text-b2b-headline -mb-px";
export const b2bWorkspaceTabActive = `${b2bWorkspaceTab} border-b-b2b-accent text-b2b-accent`;
export const b2bWorkspaceTabInactive = b2bWorkspaceTab;

/** Station review tabs (Transcript / Feedback / GP Lead) — one body scale. */
export const b2bStationReviewBody = "text-osce-body leading-relaxed";
export const b2bStationReviewSectionTitle =
  "text-osce-body font-semibold text-b2b-headline";
export const b2bStationReviewMuted = "text-osce-body text-b2b-mid";

export const b2bTabPillRoundActive =
  "rounded-md bg-b2b-accent px-4 py-2 text-osce-body font-medium text-white";
export const b2bTabPillRoundInactive =
  "rounded-md bg-b2b-cream px-4 py-2 text-osce-body font-medium text-b2b-mid hover:text-b2b-headline";
export const b2bWizardTabActive =
  "border-b-2 border-b2b-accent py-2 px-3 text-osce-body font-medium text-b2b-accent transition-all whitespace-nowrap md:px-4";
export const b2bWizardTabInactive =
  "border-b-2 border-transparent py-2 px-3 text-osce-body font-medium text-b2b-mid transition-all hover:text-b2b-headline whitespace-nowrap md:px-4";
export const b2bStepCircleActive =
  "flex h-7 w-7 items-center justify-center rounded-full bg-b2b-accent text-osce-caption font-medium text-white";
export const b2bStepCircleInactive =
  "flex h-7 w-7 items-center justify-center rounded-full bg-b2b-subtle text-osce-body font-medium text-b2b-mid";
export const b2bWizardStepCircleActive =
  "flex h-6 w-6 items-center justify-center rounded-full bg-b2b-accent text-osce-caption font-medium text-white md:h-8 md:w-8";
export const b2bWizardStepCircleInactive =
  "flex h-6 w-6 items-center justify-center rounded-full bg-b2b-subtle text-osce-body font-medium text-b2b-mid md:h-8 md:w-8 md:text-osce-body";
export const b2bBadgeNumeric =
  "inline-flex h-6 w-6 items-center justify-center rounded-full bg-b2b-accent text-osce-caption font-semibold text-white"; /** Sidebar nav link. Active / inactive states */
export const b2bNavLink =
  "flex items-center rounded-md px-3 py-2 text-osce-body font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-b2b-headline/10";
export const b2bNavLinkActive = `${b2bNavLink} bg-b2b-accent-bg text-b2b-accent`;
export const b2bNavLinkInactive = `${b2bNavLink} text-b2b-mid hover:bg-b2b-cream hover:text-b2b-headline`;

export type B2BIconTooltipPlacement = "bottom" | "left" | "top" | "right";

/** Wrapper for icon-only controls that show a hover/focus tooltip chip. */
export const b2bIconTooltipShell = "group relative inline-flex";

/** Chip visuals only — no positioning, so it can be portalled to the body. */
export const b2bIconTooltipChipBase =
  "pointer-events-none z-[200] w-max max-w-[220px] rounded-md border border-b2b-border bg-b2b-headline px-3 py-1.5 text-osce-caption text-white";

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
  "absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-b2b-headline";

export const b2bIconButtonGhost = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border-0 bg-transparent text-b2b-mid hover:bg-b2b-cream hover:text-b2b-headline disabled:pointer-events-none disabled:opacity-50 ${b2bIconFocus}`;
/** Borders for the template builder (Start + Structure) and workspace chrome. */
export const b2bBuilderHairlineColor = "border-b2b-border";
export const b2bBuilderHairline = `border ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineB = `border-b ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineR = `border-r ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineL = `border-l ${b2bBuilderHairlineColor}`;
export const b2bBuilderHairlineT = `border-t ${b2bBuilderHairlineColor}`;
export const b2bBuilderDivideY = "divide-y divide-b2b-border";
/** Selected card border in the template builder (Start layout cards + Structure field cards). */
export const b2bBuilderCardSelected =
  "border border-b2b-accent-border bg-b2b-accent-bg";
export const b2bBuilderCardSelectedDivider = "border-b border-b2b-accent-border";
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
export const b2bPageChromeHeader = `bg-b2b-surface ${b2bBuilderHairlineB}`; /** Main scroll region in signed-in workspace shells (org, platform, partner, practice, trainee). */
export const b2bShellMain =
  `${b2bBuilderScrollY} w-full min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden bg-b2b-canvas pb-[max(1rem,env(safe-area-inset-bottom,0px))] pt-[calc(4rem+env(safe-area-inset-top,0px))] lg:pb-0 lg:pt-0`; /** Scroll wrapper for wide data tables inside cards. */
export const b2bTableScroll =
  "min-w-0 overflow-x-auto [-webkit-overflow-scrolling:touch]"; /** * Title row + actions: stacks on mobile, side-by-side from `sm`. * Use on custom headers when not using {@link B2BPageHeader}. */
export const b2bStackHeaderRow =
  "flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between"; /** Modal / form footer actions. Stack on narrow viewports. */
export const b2bModalFooterActions =
  "flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row sm:items-center sm:justify-end sm:gap-3"; /** Horizontal tab strip that wraps or scrolls on small screens. */
export const b2bTabStrip =
  `${b2bWorkspaceTabStrip} gap-0 overflow-x-auto [-webkit-overflow-scrolling:touch]`; /** Wizard / step footer: Back + Continue. */
export const b2bWizardFooter =
  "flex flex-col-reverse gap-3 border-t border-b2b-border px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6"; /** Ghost outline button (Connect ↗ pattern) */
export const b2bGhostButton =
  "inline-flex items-center gap-1.5 rounded-md border border-b2b-border bg-white px-3 py-1.5 text-osce-body font-medium text-b2b-headline transition-colors hover:bg-b2b-cream focus:outline-none focus:ring-2 focus:ring-b2b-headline/10";
/** Solid black CTA. Use instead of raw `bg-b2b-accent` For inline `<button>` / `<a>`. */
export const b2bButtonPrimary =
  "inline-flex items-center justify-center gap-2 rounded-md border border-transparent bg-b2b-accent px-4 py-2 text-osce-body font-medium text-white transition-colors hover:bg-b2b-accent-hover focus:outline-none focus:ring-2 focus:ring-b2b-accent/30 disabled:pointer-events-none disabled:opacity-60";
export const b2bButtonPrimarySm =
  "inline-flex items-center gap-1 rounded-md border border-transparent bg-b2b-accent px-2 py-1 text-osce-caption font-medium text-white hover:bg-b2b-accent-hover disabled:opacity-50";
export const b2bButtonPrimaryLg =
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-lg border border-transparent bg-b2b-accent px-6 py-3 text-osce-body font-semibold text-white transition-colors hover:bg-b2b-accent-hover focus:outline-none focus:ring-2 focus:ring-b2b-accent/30 disabled:pointer-events-none disabled:opacity-60";
/** Alias of {@link b2bButtonPrimary} for explicit accent intent. */
export const b2bButtonAccent =
  "inline-flex items-center justify-center gap-2 rounded-md border border-transparent bg-b2b-accent px-4 py-2 text-osce-body font-medium text-white transition-colors hover:bg-b2b-accent-hover focus:outline-none focus:ring-2 focus:ring-b2b-accent/30 disabled:pointer-events-none disabled:opacity-60";

/** Stat / metric tile on dashboards. */
export const b2bStatCard =
  "flex min-w-0 flex-1 flex-col gap-2 rounded-lg border border-b2b-border bg-b2b-surface p-4 transition-colors hover:border-b2b-accent-border hover:bg-b2b-accent-bg/30";

export const b2bStatCardValue =
  "text-osce-title font-semibold tabular-nums tracking-tight text-b2b-headline";

export const b2bStatCardLabel =
  "text-osce-meta font-medium text-b2b-mid";

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
  "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md";

/** Semantic alert / badge surface tokens (pair with text-* and border-*). */
export const b2bSemanticSuccess =
  "bg-b2b-success-bg border-b2b-success-border text-b2b-success-text";
export const b2bSemanticWarning =
  "bg-b2b-warning-bg border-b2b-warning-border text-b2b-warning-text";
export const b2bSemanticDanger =
  "bg-b2b-danger-bg border-b2b-danger-border text-b2b-danger-text";
export const b2bSemanticInfo =
  "bg-b2b-info-bg border-b2b-info-border text-b2b-info-text";

/** Auth route canvas — classic landing gradient on quiet surfaces (login, change-password). */
export const b2bAuthCanvas =
  "bg-[linear-gradient(180deg,#F5F7FA_0%,#FBFCFD_62%,#FFFFFF_100%)]";
