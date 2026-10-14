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
/** * Shared Tailwind class strings for B2C app surfaces. * Primary CTAs: classic landing blue (`Button variant="primary"` / `b2cButtonPrimary`). * Links / accents: `b2c-primary`, `b2cLink`. * * See `docs/DESIGN.md`. */
import { getButtonClassName } from "@/foundation/ui/buttonStyles";
import { cardScrollBody, getCardSurfaceClasses } from "@/foundation/ui/Card";
import { getInputClassName } from "@/foundation/ui/inputStyles";
const b2cIconFocus =
  "focus:outline-none focus:ring-2 focus:ring-osce-accent/20 focus:ring-offset-1 rounded-md";
export const b2cIconButton = `inline-flex h-11 w-11 shrink-0 sm:h-9 sm:w-9 items-center justify-center rounded-control border border-transparent bg-transparent text-b2c-text-secondary hover:bg-b2c-secondary hover:text-osce-ink-900 disabled:pointer-events-none disabled:opacity-50 ${b2cIconFocus}`;
export const b2cLink =
  "font-medium text-osce-accent hover:text-osce-accent-hover";
export const b2cInputBase = getInputClassName();

/** Hairline card chrome — always use on card surfaces (#E4E7EC border). */
export const b2cCard = getCardSurfaceClasses();
/** Tinted square icon holder — matches B2B doctor prep / {@link B2BIconChip}. */
export const b2cSectionIconChipBase =
  "inline-flex shrink-0 items-center justify-center rounded-osce-md";

export const SCA_ABOUT_MODAL_WIDTH = "600px";
export const SCA_ABOUT_BAND_MODAL_WIDTH = "480px";
/** Nested chart inset — muted fill, still keeps a visible hairline border. */
export const b2cDashboardChartWell =
  "rounded-control bg-b2c-surface-muted p-3 sm:p-4";
export const b2cCardPadding = "p-4 sm:p-5";
export const b2cPanelDivided = `${b2cCard} ${cardScrollBody} divide-y divide-b2c-border-light`;
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
    card: "border-b2c-border bg-osce-surface-inset",
    header: "border-b2c-border bg-osce-accent-muted text-osce-ink-900",
    title: "text-osce-ink-900",
    body: "text-osce-ink-700",
    list: "text-osce-ink-700 marker:text-osce-ink-400",
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
export const b2cHeroTitle =
  "text-osce-heading font-semibold tracking-[-0.022em] text-osce-ink-900";
export const b2cGroupedShell = `${b2cCard} min-w-0 max-w-full overflow-hidden`;
export const b2cGroupedRow =
  "flex min-h-[54px] items-center gap-3 border-b border-b2c-border-light px-4 py-[9px] transition-colors last:border-b-0 hover:bg-b2c-secondary";
export const b2cGroupedRowTitle =
  "text-osce-body font-medium leading-[19px] text-osce-ink-900";
export const b2cGroupedRowSubtitle =
  "mt-[3px] text-osce-meta text-b2c-text-muted";
/** A headline number: mono, 28/34 (canvas `train-achievements`). */
export const b2cMetric = "font-mono text-[28px] leading-[34px] tabular-nums text-osce-ink-900";
/** The one hero per screen: a grey panel, no border (canvas `train-dashboard`). */
export const b2cHeroCtaSurface =
  "block w-full rounded-osce-2xl bg-b2c-surface-muted px-6 py-6 sm:px-8 sm:py-7";
export const b2cCardPlain = `${b2cCard} min-w-0 max-w-full`;
/** Page title: Fraunces 600, 30/36 (canvas `h1.t1`). */
export const b2cPageTitle =
  "font-title text-osce-display-sm font-semibold tracking-[-0.015em] text-osce-ink-900";
export const b2cPageHeaderShell = "mb-6 sm:mb-8";
export const b2cPageHeaderTitle = b2cPageTitle;
/** Large numeric / stat emphasis (dashboard scores, percentages). */
export const b2cStatValue =
  "text-osce-heading font-semibold tabular-nums tracking-tight text-osce-ink-900";
/** Card / section title (canvas `.t3`, 15/21 600). */
export const b2cSectionTitle =
  "text-osce-subheading font-semibold tracking-[-0.006em] text-osce-ink-900";
export const b2cBodyText =
  "text-osce-body leading-relaxed text-b2c-text-secondary";
export const b2cBodyTextMuted =
  "text-osce-body leading-relaxed text-b2c-text-muted";
/** Default card header band. metadata (@user · date), 16px. */
export const b2cPanelCardHeader =
  "text-osce-body font-medium text-b2c-text-secondary";
export const b2cPanelCardMeta =
  "text-osce-body font-normal text-b2c-text-muted";
/** Modal / page section headings inside panel flows. */
/** Modal title (canvas `.t2`, 19/25 600). */
export const b2cModalTitle =
  "text-osce-title font-semibold tracking-[-0.016em] break-words text-osce-ink-900";
export const b2cModalHelper =
  "mt-0.5 text-osce-body leading-relaxed text-b2c-text-muted";
/** Settings tabs — shared field + checkbox typography. */
export const b2cSettingsFieldInput = `${b2cInputBase} py-2.5`;
export const b2cSettingsFieldInputDisabled =
  "mt-1.5 w-full cursor-not-allowed rounded-control border border-b2c-border bg-b2c-secondary px-3 py-2.5 text-osce-body text-b2c-text-secondary";
export const b2cSettingsCheckboxTitle =
  "mb-1.5 flex items-center gap-2.5 text-osce-body font-semibold leading-snug text-osce-ink-900";
export const b2cSettingsCheckboxHelper =
  "block text-osce-body leading-relaxed text-b2c-text-muted";
export const b2cSettingsOptionRow =
  "rounded-osce-lg border border-b2c-border px-4 py-4 sm:px-5";
export const b2cSettingsCardHeaderIcon = "h-4 w-4 shrink-0 text-osce-ink-500";
/** Picker tiles (A–Z, specialty, tag chips). */
export const b2cPickerChipBase =
  "inline-flex items-center justify-center rounded-osce-lg border text-osce-body font-medium transition-colors";
export const b2cPickerChip =
  `${b2cPickerChipBase} border-b2c-border bg-osce-surface text-b2c-text-secondary hover:bg-b2c-surface-muted`;
export const b2cPickerChipSelected =
  "border-osce-ink-900 bg-osce-ink-900 !text-white";
export const b2cPickerChipUnselected =
  "border-b2c-border bg-osce-surface text-b2c-text-secondary hover:bg-b2c-surface-muted";
/** Rows inside panel cards (topic lists, dropdown results). */
export const b2cPanelListRow =
  "group flex min-h-[54px] items-center justify-between gap-3 border-b border-b2c-border-light px-4 py-[9px] text-left transition-colors last:border-b-0 hover:bg-b2c-surface-muted";
export const b2cPanelListRowTitle =
  "min-w-0 text-osce-body font-medium text-osce-ink-900";
export const b2cDropdownItem =
  "block w-full px-3 py-2.5 text-left text-osce-body text-osce-ink-900 transition hover:bg-b2c-surface-muted";
/** Segmented control (canvas `.seg`): grey track, white raised active item. */
export const b2cSegmentedControl =
  "inline-flex max-w-full min-w-0 flex-nowrap items-center gap-0.5 self-start overflow-x-auto overflow-y-hidden overscroll-x-contain touch-pan-x rounded-control bg-b2c-surface-muted p-0.5";
/** Standard gap below a page-level tab row (matches Settings, Community, Mocks). */
export const b2cSegmentedTabsSpacing = "mb-6";
export const b2cSegmentedTab =
  "inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-[7px] px-3 text-[13px] font-medium leading-none whitespace-nowrap transition-colors sm:h-7";
export const b2cSegmentedTabLabel = "inline-block";
export const b2cSegmentedTabActive = `${b2cSegmentedTab} bg-osce-surface text-osce-ink-900 shadow-[0_1px_2px_rgba(0,0,0,0.08),0_0_0_0.5px_rgba(0,0,0,0.04)]`;
export const b2cSegmentedTabInactive = `${b2cSegmentedTab} text-b2c-text-muted hover:text-osce-ink-900`;
export const b2cSegmentedTabLabelActive = b2cSegmentedTabLabel;
export const b2cSegmentedTabLabelInactive = b2cSegmentedTabLabel;
/**
 * Eyebrow over a title or a list (canvas `.ey`): 12.5/18, sentence case. The
 * name predates the redesign; it is no longer mono or uppercase.
 */
export const b2cMonoEyebrow = "text-osce-meta font-medium text-b2c-text-muted";
/** Pill (canvas `.pill`): 22px, radius 6, 12/16 medium. */
export const b2cBandPillBase =
  "inline-flex h-[22px] w-fit items-center gap-1.5 whitespace-nowrap rounded-osce-sm border px-2 text-osce-caption font-medium";
export const b2cBandPillCompetent =
  `${b2cBandPillBase} border-osce-band-competentBorder bg-osce-band-competentBg text-osce-band-competent`;
export const b2cBandPillDeveloping =
  `${b2cBandPillBase} border-osce-band-developingBorder bg-osce-band-developingBg text-osce-band-developing`;
export const b2cBandPillDevelopment =
  `${b2cBandPillBase} border-osce-band-developmentBorder bg-osce-band-developmentBg text-osce-band-development`;
/** Sidebar — solid white surface, distinct from muted content canvas */
/** Sidebar: sits on the canvas grey; the main panel is the white surface. */
export const b2cNavShell =
  "bg-osce-canvas border-b2c-border font-sans text-osce-data antialiased";
/** Fixed mobile top bar — matches sidebar surface */
export const b2cNavMobileBar = "bg-osce-canvas border-b border-b2c-border";
export const b2cNavSectionLabel =
  "px-2.5 pb-1.5 pt-[18px] text-[11.5px] font-semibold leading-4 text-osce-ink-400";
/** Nav item (canvas `.nav`): 32px, 13.5px, radius 8, 16px muted icon. */
export const b2cNavLink =
  "relative flex min-h-11 items-center gap-2.5 rounded-osce-md px-2.5 text-osce-data font-medium transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-osce-accent/30 md:min-h-8 [&_svg]:h-4 [&_svg]:w-4";
/** The current page is a raised white pill; hover stays the flat grey, so the two never read alike. */
export const b2cNavLinkActive = `${b2cNavLink} border border-osce-border bg-osce-surface font-semibold text-osce-ink-900 shadow-sm [&_svg]:text-osce-accent`;
export const b2cNavLinkInactive = `${b2cNavLink} text-osce-ink-700 hover:bg-osce-navActive hover:text-osce-ink-900 [&_svg]:text-osce-ink-500`;
/** Sidebar upgrade — solid primary; blue reserved for intentional CTAs only. */
export const b2cNavUpgradeButton =
  "inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-control border border-b2c-border bg-osce-surface px-3.5 text-osce-body font-medium text-osce-ink-900 transition-colors hover:bg-b2c-secondary focus:outline-none focus:ring-2 focus:ring-osce-accent/20";
/** Chip visuals only — no positioning, so it can be portalled to the body. */
export const b2cNavTooltipChip =
  "pointer-events-none z-[100] whitespace-nowrap rounded-osce-md border border-transparent bg-osce-ink-900 px-3 py-1.5 text-osce-meta font-medium text-osce-surface";
export const b2cNavTooltipArrow =
  "absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-b2c-text-primary";
/** The page column (canvas: max 1200, centred, 24px between blocks). */
export const b2cPageColumn =
  "mx-auto w-full min-w-0 max-w-osce-page space-y-6 overflow-x-hidden";
export const b2cScrollY = "overflow-y-auto overflow-x-hidden";

/**
 * A live room (station, peer session) laid over the content column, toolbar
 * included. On phones it starts under the fixed 56px top bar instead of at the
 * column's top: iOS gives the scrolling main its own stacking context, so the
 * room's z-index cannot lift it over that bar and the bar hid the clock.
 *
 * The room is its own page scroller. Only from `lg`, where its panes sit side
 * by side, is it a flex column whose panes share its height and scroll inside
 * themselves; below that it is a block, so stacked panes keep their natural
 * height and the room scrolls. A fixed-height flex column on a phone squeezed
 * the panes into the screen and clipped them, with nothing left to scroll.
 * The bottom padding clears the floating Help button, as `b2cShellMain`'s does.
 */
export const b2cRoomOverlay = [
  "absolute inset-x-0 bottom-0 top-14 z-30 md:top-0",
  "overflow-y-auto overflow-x-hidden overscroll-y-contain bg-osce-canvas [-webkit-overflow-scrolling:touch]",
  "pb-[calc(0.5rem+2.75rem+env(safe-area-inset-bottom,0px))] md:pb-0 lg:flex lg:flex-col",
].join(" ");

/** A link in a live room's fill chain: from `lg` it takes the room's leftover height; below, its natural height. */
export const b2cRoomFill = "lg:flex lg:min-h-0 lg:flex-1 lg:flex-col";

export const b2cShellMain = [
  "w-full min-h-0 min-w-0 flex-1 bg-osce-surface",
  // Canvas: 36px 40px 56px under the toolbar; the top 36px is the page column's
  // (WorkspaceShell), so sticky blocks stick flush under the toolbar. Mobile clears the fixed top bar
  // (pt-16) and the floating help button at the bottom.
  "px-4 pt-20 md:pt-0 pb-[calc(0.5rem+2.75rem+env(safe-area-inset-bottom,0px))] sm:px-6 lg:px-10 lg:pb-14",
  "[-webkit-overflow-scrolling:touch] overscroll-y-contain",
  b2cScrollY,
].join(" ");
/** Horizontal table scroll only. do not use touch-pan-x / overflow-y-hidden (they trap vertical page scroll on mobile). */
export const b2cTableScroll =
  "min-w-0 max-w-full overflow-x-auto overscroll-x-contain [-webkit-overflow-scrolling:touch]";
/** Column headers (canvas `th`): 12/16 medium, muted, sentence case. */
export const b2cTableHeader =
  "text-osce-caption font-medium text-b2c-text-secondary";
/** Table head band: transparent over a hairline. */
export const b2cTableThead = "bg-transparent";
/** Data cells — Inter at 14px (between body-sm and body). */
export const b2cTableCell =
  "font-sans text-osce-data text-osce-ink-900";
/** Use in column `render` props so cell content matches `b2cTableCell`. */
export const b2cTableCellText =
  "font-sans text-osce-data text-osce-ink-900";
export const b2cGhostButton =
  "inline-flex h-9 items-center justify-center gap-1.5 rounded-control border border-b2c-border bg-osce-surface px-4 text-osce-body font-medium text-osce-ink-900 transition-colors hover:bg-b2c-secondary focus:outline-none focus:ring-2 focus:ring-osce-accent/20"; /** Blue primary CTA. Default for B2C actions. */
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
  "b2c-livekit-end-button inline-flex h-9 items-center justify-center gap-1.5 rounded-control border border-transparent bg-osce-danger-hover px-4 text-osce-body font-medium text-white shadow-sm transition-colors hover:bg-osce-danger-text focus:outline-none focus:ring-2 focus:ring-osce-danger-border focus:ring-offset-1 disabled:pointer-events-none disabled:opacity-60";
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
