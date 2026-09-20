"use client";

import { Card, type CardProps } from "@/foundation/ui";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

export function AuthoringCard(props: CardProps) {
  const chrome = useAuthoringChrome();
  return <Card {...props} themeType={props.themeType ?? chrome.themeType} />;
}
