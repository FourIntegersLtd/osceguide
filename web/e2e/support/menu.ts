import { expect, type Page } from "@playwright/test";

/** The workspace sidebar: the shell labels its navigation landmark "<arm> sections". */
export const sidebar = (page: Page) => page.getByRole("navigation", { name: / sections$/ }).first();

/** The links the signed-in role is shown (and not shown) in the sidebar, by exact label. */
export async function expectMenu(page: Page, { shows, hides = [] }: { shows: string[]; hides?: string[] }): Promise<void> {
  const menu = sidebar(page);
  for (const label of shows) await expect(menu.getByRole("link", { name: label, exact: true }).first(), `menu shows ${label}`).toBeVisible();
  for (const label of hides) await expect(menu.getByRole("link", { name: label, exact: true }), `menu hides ${label}`).toHaveCount(0);
}

/** The page rendered a level-1 heading (optionally a specific one). */
export async function expectPageHeading(page: Page, name?: string | RegExp): Promise<void> {
  await expect(page.getByRole("heading", { level: 1, ...(name ? { name } : {}) }).first()).toBeVisible();
}
