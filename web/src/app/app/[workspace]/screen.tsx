"use client";

import { createElement } from "react";
import { notFound } from "next/navigation";
import { useSession } from "@/foundation/session";
import { resolveWorkspace, screenComponent, surfaceForWorkspace } from "@/surfaces";
import type { ScreenName } from "@/surfaces";

/**
 * The one place a page's arm-dependence is resolved.
 *
 * `/app/me/dashboard` and `/app/kings/dashboard` are one route file. Which
 * component answers comes from the arm's screen map, so a page never branches
 * and adding an arm adds no route files at all. An arm that does not declare
 * the screen renders a 404, which is how `/app/kings/mocks` — a consumer page
 * asked of an institution — comes out right without anybody listing the
 * combinations.
 */
export function Screen({
  name,
  slug,
  params,
}: {
  name: ScreenName;
  slug: string;
  params?: Record<string, string>;
}) {
  const { session } = useSession();
  const workspace = resolveWorkspace(slug, session?.user ?? null);
  if (!workspace) notFound();

  const screen = screenComponent(surfaceForWorkspace(workspace), name);
  if (!screen) notFound();

  /*
   * `createElement` rather than `<Screen />` from a local binding: the React
   * Compiler reads an assignment to a capitalised local as defining a
   * component during render, which is the real mistake it is looking for. This
   * is a lookup in a table fixed at module scope, and saying so directly is
   * clearer than suppressing the rule.
   */
  return createElement(screen, { workspace, params });
}
