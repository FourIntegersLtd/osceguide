"use client";

import { createElement, useEffect, useState } from "react";
import { notFound } from "next/navigation";
import { PageSpinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { loadScreenComponent, ownsScreen, resolveWorkspace, surfaceForWorkspace } from "@/surfaces";
import type { ScreenName } from "@/surfaces";
import type { ScreenProps } from "@/surfaces/contract";
import type { ComponentType } from "react";
import { NotOnThisAccount } from "@/surfaces/hire/NotOnThisAccount";

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

  const manifest = surfaceForWorkspace(workspace);
  // The manifest is the declared list; the screen map is the implementation. A name
  // the manifest does not own is a 404 even if a map happens to have it.
  if (!ownsScreen(manifest, name)) {
    // An employer's candidate who follows a learner's link is told why, not shown a bare 404 (HireRefused).
    if (manifest.id === "hire") return <NotOnThisAccount workspace={workspace} />;
    notFound();
  }
  const surfaceKey = manifest.screensFrom ?? manifest.id;

  return (
    <ResolvedScreen
      key={`${surfaceKey}-${name}`}
      manifest={manifest}
      name={name}
      workspace={workspace}
      params={params}
    />
  );
}

function ResolvedScreen({
  manifest,
  name,
  workspace,
  params,
}: {
  manifest: ReturnType<typeof surfaceForWorkspace>;
  name: ScreenName;
  workspace: NonNullable<ReturnType<typeof resolveWorkspace>>;
  params?: Record<string, string>;
}) {
  const [screen, setScreen] = useState<ComponentType<ScreenProps> | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    void loadScreenComponent(manifest, name).then((component) => {
      if (cancelled) return;
      // `setScreen(Fn)` is an updater: React would call `Fn(prev)` and store
      // the JSX it returned. Wrap so the component itself is the state.
      setScreen(() => component ?? null);
    });
    return () => {
      cancelled = true;
    };
  }, [manifest, name]);

  if (screen === undefined) {
    return (
      <PageSpinner fill="section" />
    );
  }

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
