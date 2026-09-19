/*
 * The product's class-name vocabulary, brought across from the retiring
 * client's `b2c/theme/b2cUi.ts`.
 *
 * Every string here is a Tailwind class list naming the `osce-*` palette in
 * `osceTokens.css`. The ported screens reference these by name rather than
 * repeating the classes, which is why a change to the card border is one edit
 * rather than ninety.
 *
 * New code should prefer the primitives in this folder — `Card`, `Button`,
 * `PageHeader` — which are built from the semantic tokens and therefore skin
 * correctly on every arm. These exist so a ported screen keeps looking exactly
 * as it does today.
 */
/** * Shared Tailwind class strings for B2C app surfaces. * Primary CTAs: classic landing blue (`Button variant="primary"` / `b2cButtonPrimary`). * Links / accents: `b2c-primary`, `b2cLink`. * * See `.cursor/rules/b2c-design-language.mdc`. */
import { getButtonClassName } from "@/foundation/ui/buttonStyles";
import { getCardSurfaceClasses } from "@/foundation/ui/Card";
import { getInputClassName } from "@/foundation/ui/inputStyles";
const b2cIconFocus =
  "focus:outline-none focus:ring-2 focus:ring-osce-accent/20 focus:ring-offset-1 rounded-md";
export const b2cIconButton = `inline-flex h-11 w-11 shrink-0 sm:h-9 sm:w-9 items-center justify-center rounded-md border border-b2c-border bg-osce-surface text-b2c-text-secondary hover:bg-b2c-secondary disabled:pointer-events-none disabled:opacity-50 ${b2cIconFocus}`;
export const b2cLink =
  "font-medium text-osce-accent hover:text-osce-accent-hover";
export const b2cLinkMuted =
  "font-medium text-b2c-text-muted hover:text-osce-ink-900";
/** Secondary “About” control on dashboard cards — muted until hover. */
export const b2cAboutLink =
  "text-osce-meta font-medium text-b2c-text-muted transition-colors hover:text-osce-accent";
/**
 * @deprecated Focus styling belongs to the shared control; kept only for
 * call sites that compose it onto a non-input element.
 */
export const b2cInputFocus =
  "focus:border-osce-accent focus:outline-none focus:ring-2 focus:ring-osce-accent-subtle";
export const b2cInputBase = getInputClassName();

/** Hairline card chrome — always use on card surfaces (#E4E7EC border). */
export const b2cCardShell = getCardSurfaceClasses();
/** SCA About modal — quiet help card (no shadow). */
export const b2cAboutCard = b2cCardShell;
/** Tinted square icon holder — matches B2B doctor prep / {@link B2BIconChip}. */
export const b2cSectionIconChipBase =
  "inline-flex shrink-0 items-center justify-center rounded-md";

/** @deprecated Use `B2CSectionIconBadge` from `@/foundation/ui/B2CSectionIconBadge`. */
export const b2cAboutIconWell =
  "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-osce-accent-muted text-osce-accent";
export const SCA_ABOUT_MODAL_WIDTH = "600px";
export const SCA_ABOUT_BAND_MODAL_WIDTH = "480px";
/** App card — clinical calm: 10px radius, subtle border, light shadow. */
/** @deprecated Cards are flat — use `b2cCard`. Kept so call sites need not churn. */
export const b2cCardElevated = b2cCardShell;
/** Dashboard card — same shell as app cards (screen 4D). */
export const b2cDashboardCard = b2cCardElevated;
/** Nested chart inset — muted fill, still keeps a visible hairline border. */
export const b2cDashboardChartWell =
  "rounded-lg border border-b2c-border bg-b2c-surface-muted p-3 sm:p-4";
/** Quiet panel surface. Uses elevated styling in the logged-in app shell. */
export const b2cCard = b2cCardElevated;
export const b2cCardPadding = "p-4 sm:p-5 lg:p-6";
/** Rare nested hierarchy inside a panel. not a second outer card. */
export const b2cInset = b2cCardShell;
export const b2cPanelDivided = `${b2cCard} overflow-hidden divide-y divide-b2c-border`;
export const b2cPanelSection = "px-4 py-3.5 sm:px-5 sm:py-4";
export const b2cMutedBand = "bg-b2c-surface-muted";
export const b2cFieldLabel = "text-osce-meta text-b2c-text-muted";
export const b2cFieldValue = "text-osce-body font-medium text-osce-ink-900";

/**
 * Pastel reading surfaces for long-read educational content only
 * (tips, A–Z sections, management InfoCards). App chrome stays white.
 */
export type B2CReadingTone = {
  card: string;
  header: string;
  title: string;
  body: string;
  list: string;
};

export const b2cReadingTones = {
  /** History taking, social context, ICE, the patient's story. */
  history: {
    card: "border-osce-tone-history-border bg-osce-tone-history-bg",
    header:
      "border-osce-tone-history-border bg-osce-tone-history-header text-osce-tone-history-text",
    title: "text-osce-tone-history-text",
    body: "text-osce-tone-history-body",
    list: "text-osce-tone-history-body marker:text-osce-tone-history-text",
  },
  /** Examination findings and investigations. */
  examination: {
    card: "border-osce-tone-examination-border bg-osce-tone-examination-bg",
    header:
      "border-osce-tone-examination-border bg-osce-tone-examination-header text-osce-tone-examination-text",
    title: "text-osce-tone-examination-text",
    body: "text-osce-tone-examination-body",
    list: "text-osce-tone-examination-body marker:text-osce-tone-examination-text",
  },
  /** Differential diagnosis and assessment — the thinking. */
  reasoning: {
    card: "border-osce-tone-reasoning-border bg-osce-tone-reasoning-bg",
    header:
      "border-osce-tone-reasoning-border bg-osce-tone-reasoning-header text-osce-tone-reasoning-text",
    title: "text-osce-tone-reasoning-text",
    body: "text-osce-tone-reasoning-body",
    list: "text-osce-tone-reasoning-body marker:text-osce-tone-reasoning-text",
  },
  /** Management plan, medication, non-pharmacological treatment. */
  management: {
    card: "border-osce-tone-management-border bg-osce-tone-management-bg",
    header:
      "border-osce-tone-management-border bg-osce-tone-management-header text-osce-tone-management-text",
    title: "text-osce-tone-management-text",
    body: "text-osce-tone-management-body",
    list: "text-osce-tone-management-body marker:text-osce-tone-management-text",
  },
  /** Red flags, immediate actions, safety-netting and follow-up. */
  safety: {
    card: "border-osce-tone-safety-border bg-osce-tone-safety-bg",
    header:
      "border-osce-tone-safety-border bg-osce-tone-safety-header text-osce-tone-safety-text",
    title: "text-osce-tone-safety-text",
    body: "text-osce-tone-safety-body",
    list: "text-osce-tone-safety-body marker:text-osce-tone-safety-text",
  },
  /** Patient education, advice, and supporting notes. */
  education: {
    card: "border-osce-tone-education-border bg-osce-tone-education-bg",
    header:
      "border-osce-tone-education-border bg-osce-tone-education-header text-osce-tone-education-text",
    title: "text-osce-tone-education-text",
    body: "text-osce-tone-education-body",
    list: "text-osce-tone-education-body marker:text-osce-tone-education-text",
  },
  /**
   * Candidate coaching, not clinical content — exam technique and
   * "try this" prompts. These never sit alongside the stage tones.
   */
  tip: {
    card: "border-osce-accent-subtle bg-osce-accent-muted",
    header:
      "border-osce-accent-subtle bg-osce-accent-subtle/70 text-osce-accent-hover",
    title: "text-osce-accent-hover",
    body: "text-osce-accent-hover/90",
    list: "text-osce-accent-hover marker:text-osce-accent",
  },
  practice: {
    card: "border-osce-tone-education-border bg-osce-tone-education-bg",
    header:
      "border-osce-tone-education-border bg-osce-tone-education-header text-osce-tone-education-text",
    title: "text-osce-tone-education-text",
    body: "text-osce-tone-education-body",
    list: "text-osce-tone-education-body marker:text-osce-tone-education-text",
  },
} as const satisfies Record<string, B2CReadingTone>;

export type B2CReadingToneKey = keyof typeof b2cReadingTones;

/**
 * Cycle used by psychosocial A–Z aspect cards. Colour is positional here,
 * not semantic — the aspects are a dynamic list with no consultation stage,
 * so the rotation only separates neighbouring cards. It stays inside the
 * same six hues so the palette remains closed.
 */
export const b2cPsychosocialReadingToneKeys = [
  "history",
  "examination",
  "reasoning",
  "management",
  "education",
  "safety",
] as const satisfies readonly B2CReadingToneKey[];

export const b2cEyebrow = "text-osce-meta font-medium text-b2c-text-muted";
export const b2cProseMeasure = "max-w-2xl";
export const b2cProseMeasureWide = "max-w-3xl";
export const b2cProseMeasureTight = "max-w-xl";
export const b2cHeroTitle =
  "font-heading text-osce-title font-semibold leading-tight tracking-tight text-osce-ink-900";
export const b2cHeroSubtitle =
  "text-osce-body leading-relaxed text-b2c-text-muted";
export const b2cGroupedShell = `${b2cCard} min-w-0 max-w-full overflow-hidden`;
export const b2cGroupedRow =
  "flex min-h-[56px] items-center gap-3 border-b border-b2c-border px-4 py-3.5 transition-colors last:border-b-0 hover:bg-b2c-secondary sm:min-h-[52px] sm:py-3";
export const b2cGroupedRowTitle =
  "text-osce-body font-medium leading-snug text-osce-ink-900";
export const b2cGroupedRowSubtitle =
  "mt-0.5 text-osce-meta leading-snug text-b2c-text-muted";
export const b2cHeroCtaSurface =
  "block w-full rounded-2xl border border-b2c-border bg-osce-surface p-6 transition-colors hover:bg-b2c-secondary/60 lg:p-8";
export const b2cLinkPrimary = b2cLink;
export const b2cCardPlain = `${b2cCard} min-w-0 max-w-full`;
export const b2cPageTitle =
  "font-heading text-osce-title font-semibold tracking-[-0.025em] text-osce-ink-900";
export const b2cDashboardTitle =
  "font-heading text-osce-title font-semibold leading-[1.25] tracking-[-0.025em] text-osce-ink-900";
/** Marketing / hero display sizes (landing only). */
export const b2cDisplaySm =
  "font-heading text-osce-display-sm font-bold leading-tight tracking-tight text-osce-ink-900";
export const b2cDisplay =
  "font-heading text-osce-display font-bold leading-tight tracking-tight text-osce-ink-900";
export const b2cDisplayLg =
  "font-heading text-osce-display-lg font-bold leading-tight tracking-tight text-osce-ink-900";
export const b2cPageHeaderShell =
  "mb-4 border-b border-b2c-border pt-1 pb-3 sm:mb-6 sm:pt-4 sm:pb-5";
export const b2cPageHeaderTitle =
  "font-heading text-osce-title font-bold leading-tight text-osce-ink-900";
/** Large numeric / stat emphasis (dashboard scores, percentages). */
export const b2cStatValue =
  "text-osce-heading font-semibold tabular-nums tracking-tight text-osce-ink-900";
/** Empty-state / loading icons (react-icons). */
export const b2cIconEmptyLg = "h-12 w-12";
export const b2cIconEmptyMd = "h-10 w-10";
export const b2cSectionTitle =
  "font-heading text-osce-subheading font-semibold text-osce-ink-900";
export const b2cBodyText =
  "text-osce-body leading-relaxed text-b2c-text-secondary";
export const b2cBodyTextMuted =
  "text-osce-body leading-relaxed text-b2c-text-muted";
/** Default card header band. metadata (@user · date), 16px. */
export const b2cPanelCardHeader =
  "text-osce-body font-medium text-b2c-text-secondary";
/** Emphasised card section title. use via className when the header is a label, not metadata. */
export const b2cPanelCardTitle =
  "text-osce-subheading font-medium text-osce-ink-900";
export const b2cPanelCardMeta =
  "text-osce-body font-normal text-b2c-text-muted";
/** Modal / page section headings inside panel flows. */
export const b2cModalTitle =
  "font-heading text-osce-subheading font-semibold tracking-tight break-words text-osce-ink-900";
export const b2cModalHelper =
  "mt-0.5 text-osce-body leading-relaxed text-b2c-text-muted";
/** Settings tabs — shared field + checkbox typography. */
export const b2cSettingsFieldInput = `${b2cInputBase} py-2.5`;
export const b2cSettingsFieldInputDisabled =
  "mt-1.5 w-full cursor-not-allowed rounded-md border border-b2c-border bg-b2c-secondary px-3 py-2.5 text-osce-body text-b2c-text-secondary";
export const b2cSettingsCheckboxRow =
  "flex cursor-pointer items-start gap-3.5 sm:gap-4";
export const b2cSettingsCheckboxInput =
  "mt-1 h-5 w-5 shrink-0 rounded border-b2c-border text-osce-accent focus:ring-2 focus:ring-osce-accent/20 sm:mt-0.5";
export const b2cSettingsCheckboxTitle =
  "mb-1.5 flex items-center gap-2.5 text-osce-body font-semibold leading-snug text-osce-ink-900";
export const b2cSettingsCheckboxHelper =
  "block text-osce-body leading-relaxed text-b2c-text-muted";
export const b2cSettingsOptionRow =
  "rounded-lg border border-b2c-border px-4 py-4 sm:px-5 sm:py-5";
export const b2cSettingsIntro =
  "text-osce-body leading-relaxed text-b2c-text-muted";
export const b2cSettingsCardHeaderIcon = "h-4 w-4 shrink-0 text-osce-accent";
/** Picker tiles (A–Z, specialty, tag chips). */
export const b2cPickerChipBase =
  "inline-flex items-center justify-center rounded-none border text-osce-body font-medium transition-colors";
export const b2cPickerChip =
  `${b2cPickerChipBase} border-b2c-border bg-osce-surface text-b2c-text-secondary hover:bg-b2c-surface-muted`;
export const b2cPickerChipSelected =
  "border-osce-accent bg-osce-accent !text-white";
export const b2cPickerChipUnselected =
  "border-b2c-border bg-osce-surface text-b2c-text-secondary hover:bg-b2c-surface-muted";
export const b2cPickerChipLetter = `${b2cPickerChip} h-20 w-20 text-osce-title font-semibold sm:h-24 sm:w-24`;
export const b2cPickerChipSpecialty =
  `${b2cPickerChip} min-h-20 min-w-[11rem] px-5 py-4 text-osce-body font-semibold sm:min-h-24 sm:min-w-[12rem] sm:px-6 sm:py-5`;
/** Rows inside panel cards (topic lists, dropdown results). */
export const b2cPanelListRow =
  "group flex items-center justify-between gap-3 border-b border-b2c-border px-4 py-4 text-left transition-colors last:border-b-0 hover:bg-b2c-surface-muted sm:px-5 sm:py-3.5";
export const b2cPanelListRowTitle =
  "min-w-0 text-osce-body font-medium text-osce-ink-900 transition-colors group-hover:text-osce-accent";
export const b2cPanelSubheader =
  "border-b border-b2c-border bg-b2c-surface-muted px-4 py-2.5 text-osce-body font-medium text-b2c-text-secondary";
export const b2cDropdownItem =
  "block w-full px-3 py-2.5 text-left text-osce-body text-osce-ink-900 transition hover:bg-b2c-surface-muted";
export const b2cSegmentedControl =
  "flex w-full min-w-0 flex-nowrap items-center gap-1 overflow-x-auto overflow-y-hidden overscroll-x-contain touch-pan-x border-b border-b2c-border pb-2";
export const b2cSegmentedTab =
  "inline-flex shrink-0 items-center justify-center rounded-md border border-transparent px-3 py-2.5 text-osce-body font-medium leading-snug whitespace-nowrap transition-colors sm:px-3.5 sm:py-2";
export const b2cSegmentedTabLabel = "inline-block";
export const b2cSegmentedTabActive = `${b2cSegmentedTab} border-b2c-border bg-osce-surface text-osce-ink-900 shadow-[0_1px_2px_rgba(16,24,40,0.04)]`;
export const b2cSegmentedTabInactive = `${b2cSegmentedTab} text-b2c-text-muted hover:bg-osce-surface/70 hover:text-osce-ink-900`;
export const b2cSegmentedTabLabelActive = b2cSegmentedTabLabel;
export const b2cSegmentedTabLabelInactive = b2cSegmentedTabLabel;
export const b2cMonoEyebrow =
  "font-mono text-osce-micro font-medium uppercase tracking-[0.13em] text-b2c-text-muted";
export const b2cBandPillBase =
  "inline-flex items-center rounded-[5px] border px-[9px] py-[6px] font-mono text-osce-caption font-medium uppercase tracking-[0.09em]";
export const b2cBandPillCompetent =
  `${b2cBandPillBase} border-osce-band-competentBorder bg-osce-band-competentBg text-osce-band-competent`;
export const b2cBandPillDeveloping =
  `${b2cBandPillBase} border-osce-band-developingBorder bg-osce-band-developingBg text-osce-band-developing`;
export const b2cBandPillDevelopment =
  `${b2cBandPillBase} border-osce-band-developmentBorder bg-osce-band-developmentBg text-osce-band-development`;
/** Sidebar — solid white surface, distinct from muted content canvas */
export const b2cNavShell = "bg-osce-surface border-b2c-border-light";
/** Fixed mobile top bar — matches sidebar surface */
export const b2cNavMobileBar =
  "bg-osce-surface border-b border-[#EDF1F5]";
export const b2cNavSectionLabel =
  "mb-2.5 px-2 font-mono text-osce-micro font-medium uppercase tracking-[0.13em] text-b2c-text-muted";
export const b2cNavLink =
  "relative flex items-center gap-3 rounded-[7px] px-[11px] py-3 text-osce-body sm:py-2.5 font-normal leading-none transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-osce-accent-subtle focus-visible:ring-offset-2";
export const b2cNavLinkActive = `${b2cNavLink} bg-osce-navActive font-medium text-osce-ink-900`;
export const b2cNavLinkInactive = `${b2cNavLink} text-[#344054] hover:bg-osce-navActive hover:text-osce-ink-900`;
export const b2cNavNewPill =
  "rounded px-1.5 py-1 font-mono text-osce-micro font-medium uppercase tracking-[0.06em] text-osce-accent-hover bg-osce-accent-muted";
/** Sidebar upgrade — solid primary; blue reserved for intentional CTAs only. */
export const b2cNavUpgradeButton =
  "inline-flex w-full items-center justify-center gap-2 rounded-md border border-transparent bg-osce-accent px-4 py-2.5 text-osce-body font-medium text-white transition-colors hover:bg-osce-accent-hover focus:outline-none focus:ring-2 focus:ring-osce-accent/20";
export const b2cNavUpgradeButtonIcon =
  `${b2cNavUpgradeButton} h-11 !px-0`;
/** Chip visuals only — no positioning, so it can be portalled to the body. */
export const b2cNavTooltipChip =
  "pointer-events-none z-[100] whitespace-nowrap rounded-md border border-b2c-border bg-osce-ink-900 px-3 py-1.5 text-osce-meta font-medium text-osce-surface";
export const b2cNavTooltip =
  `${b2cNavTooltipChip} absolute left-full top-1/2 ml-3 hidden -translate-y-1/2 lg:block`;
export const b2cNavTooltipArrow =
  "absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-b2c-text-primary";
export const b2cPageColumn =
  "w-full min-w-0 max-w-full space-y-4 overflow-x-hidden sm:space-y-6";
export const b2cScrollY = "overflow-y-auto overflow-x-hidden";
export const b2cScrollX =
  "touch-pan-x overflow-x-auto overflow-y-hidden overscroll-x-contain";
/** Scroll bottom inset for collapsed help FAB — keep in sync with LivekitHelpService collapsed wrapper. */
export const b2cShellMainMobileHelpClearance =
  "calc(0.5rem+2.75rem+env(safe-area-inset-bottom,0px))";

export const b2cShellMain = [
  "w-full min-h-0 min-w-0 flex-1 bg-b2c-surface-muted",
  // Mobile: clear fixed top nav (pt-16); released at md where the nav docks
  // as a rail. Bottom pad clears the icon-only help FAB (0.5rem offset + h-11),
  // which stays a floating overlay until lg.
  "px-4 pt-16 pb-[calc(0.5rem+2.75rem+env(safe-area-inset-bottom,0px))] sm:px-6 sm:pb-[calc(0.5rem+2.75rem+env(safe-area-inset-bottom,0px))] md:pt-6 lg:px-6 lg:py-6 lg:pt-6 lg:pb-10",
  "[-webkit-overflow-scrolling:touch] overscroll-y-contain",
  b2cScrollY,
].join(" ");
/** Horizontal table scroll only. do not use touch-pan-x / overflow-y-hidden (they trap vertical page scroll on mobile). */
export const b2cTableScroll =
  "min-w-0 max-w-full overflow-x-auto overscroll-x-contain [-webkit-overflow-scrolling:touch]";
/** Column headers — IBM Plex Mono caption (matches nav eyebrows). */
export const b2cTableHeader =
  "font-mono text-osce-caption font-medium uppercase tracking-wider text-b2c-text-secondary";
/** Table head band — matches shared `Table` component. */
export const b2cTableThead = "bg-b2c-surface-muted";
/** Data cells — Inter at 14px (between body-sm and body). */
export const b2cTableCell =
  "font-sans text-osce-data text-osce-ink-900";
/** Use in column `render` props so cell content matches `b2cTableCell`. */
export const b2cTableCellText =
  "font-sans text-osce-data text-osce-ink-900";
export const b2cStackHeaderRow =
  "flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between";
export const b2cModalFooterActions =
  "flex w-full flex-col-reverse gap-2 sm:w-auto sm:flex-row sm:items-center sm:justify-end sm:gap-3";
export const b2cTabStrip =
  "flex flex-nowrap items-end gap-3 overflow-x-auto overflow-y-hidden overscroll-x-contain touch-pan-x pb-1 [-webkit-overflow-scrolling:touch] sm:gap-6 b2c-scroll-x";
export const b2cGhostButton =
  "inline-flex h-9 items-center justify-center gap-1.5 rounded-md border border-b2c-border bg-osce-surface px-4 text-osce-body font-medium text-osce-ink-900 transition-colors hover:bg-b2c-secondary focus:outline-none focus:ring-2 focus:ring-osce-accent/20"; /** Blue primary CTA. Default for B2C actions. */
export const b2cButtonPrimary = getButtonClassName({
  themeType: "b2c",
  variant: "primary",
  size: "md",
});
/**
 * Black commit CTA — the top emphasis tier, above blue `b2cButtonPrimary`.
 *
 * Reserved for the one committing action on a surface: something that changes
 * state or cannot be casually undone (start, submit, save, confirm, create,
 * claim). Navigational and repeatable primaries stay blue — view, open,
 * continue, browse, search.
 *
 * At most one black button per screen, and never on a repeated list row: a
 * black button on every row is just a black list, and the tier stops meaning
 * anything. Persistent chrome (the sidebar) sits outside this ladder entirely.
 */
export const b2cButtonCommit = getButtonClassName({
  themeType: "b2c",
  variant: "commit",
  size: "md",
});
export const b2cButtonPrimarySm = getButtonClassName({
  themeType: "b2c",
  variant: "primary",
  size: "sm",
});
export const b2cButtonPrimaryLg = getButtonClassName({
  themeType: "b2c",
  variant: "primary",
  size: "lg",
});
export const b2cButtonDanger = getButtonClassName({
  themeType: "b2c",
  variant: "danger",
  size: "md",
});
/**
 * Solid end-session control (LiveKit + voice). The `.b2c-livekit-end-button`
 * class in globals.css carries `!important` so LiveKit's own
 * `.lk-disconnect-button` theme variables cannot wash it out; these utilities
 * are the non-LiveKit fallback and use the same danger tokens.
 */
export const b2cLivekitEndButton =
  "b2c-livekit-end-button inline-flex h-9 items-center justify-center gap-2 rounded-md border border-transparent bg-osce-danger-hover px-4 text-osce-body font-medium text-white shadow-sm transition-colors hover:bg-osce-danger-text focus:outline-none focus:ring-2 focus:ring-osce-danger-border focus:ring-offset-1 disabled:pointer-events-none disabled:opacity-60";
export const b2cButtonSecondarySm = getButtonClassName({
  themeType: "b2c",
  variant: "secondary",
  size: "sm",
});
export const b2cButtonSecondary = getButtonClassName({
  themeType: "b2c",
  variant: "secondary",
  size: "md",
});
