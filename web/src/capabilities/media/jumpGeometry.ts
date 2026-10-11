/** Clear air between the sticky header and the heading a jump lands on. */
export const JUMP_GAP = 12;

/** Where to scroll the container so a section's heading sits just under the sticky header. */
export function jumpScrollTop(sectionTop: number, scrollTop: number, headerBottom: number): number {
  return Math.max(0, Math.round(sectionTop + scrollTop - headerBottom - JUMP_GAP));
}

/**
 * The sticky header's bottom edge once it sticks: the scroller's top (never above the viewport),
 * plus the header's CSS `top`, plus its height. Its bottom at rest sits lower, under the page title.
 */
export function stuckBottom(scrollerTop: number, stickyTop: number, height: number): number {
  return Math.max(0, scrollerTop) + stickyTop + height;
}

/**
 * The IntersectionObserver band a heading must cross to count as the one being read: from just
 * under the stuck header down to the top 40% of the viewport.
 */
export function readingBand(headerBottom: number): string {
  return `-${Math.round(headerBottom + JUMP_GAP)}px 0px -60% 0px`;
}
