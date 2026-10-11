/*
 * Help articles as a page. The dock is the usual way in; this is where the
 * capability's declared `/help` path lands, so a link or bookmark to it opens
 * the same article browser instead of a 404.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import HelpArticleBrowse from "@/capabilities/help/HelpArticleBrowse";

export const metadata: Metadata = {
  title: "Help",
  description: "Guides and answers about OSCE Guide.",
};

export default function Page() {
  return (
    <Capability id="help">
      <HelpArticleBrowse />
    </Capability>
  );
}
