"use client";

import { useState } from "react";
import { LuPodcast } from "react-icons/lu";
import {
  B2CPageHeader,
  B2CSegmentedTabs,
  Button,
  Modal,
  Spinner,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { isPlatformAdmin, useCurrentExam, useSession } from "@/foundation/session";
import {
  bodyMarkdown,
  isStructuredSummary,
  listAllMedia,
  podcastUrl,
  psychosocialAspects,
  summarySections,
  type MediaItem,
} from "@/capabilities/media/api";
import { ClinicalSections, PsychosocialSections } from "@/capabilities/media/SummarySections";
import { Prose } from "@/capabilities/media/Prose";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";

/**
 * An A-to-Z summary.
 *
 * Clinical and psychosocial stay two tabs, because they are read at different
 * moments — the first before a station, the second while writing one up. A
 * summary published as plain markdown instead of the three structured lists
 * falls through to the prose reader rather than showing three empty cards.
 */
export function SummaryView({
  item,
  hrefFor,
}: {
  item: MediaItem;
  hrefFor: (path: string) => string;
}) {
  const [tab, setTab] = useState<"clinical" | "psychosocial">("clinical");
  const [playing, setPlaying] = useState(false);
  const { session } = useSession();

  const sections = summarySections(item);
  const aspects = psychosocialAspects(item);
  const structured = isStructuredSummary(item);
  const audio = podcastUrl(item);
  const body = bodyMarkdown(item);
  const showTabs = structured;

  return (
    <div className="w-full text-left">
      <B2CPageHeader
        title={item.title}
        back={{ href: hrefFor(studyListPath("summary")), label: STUDY_KIND_LABEL.summary }}
        action={
          <div className="flex flex-wrap items-center gap-2">
            {audio ? (
              <Button type="button" variant="secondary" onClick={() => setPlaying(true)} className="gap-2">
                <LuPodcast className="h-4 w-4" aria-hidden />
                <span>Listen</span>
              </Button>
            ) : null}
            <DiscussWithAthena topic={{ title: item.title, kind: "summary", slug: item.slug }} />
          </div>
        }
        className="mb-6 border-b-0 pb-0 sm:pb-0"
      />

      {showTabs ? (
        <B2CSegmentedTabs
          items={[
            { id: "clinical", label: "Clinical management" },
            { id: "psychosocial", label: "Psychosocial" },
          ]}
          value={tab}
          onChange={setTab}
          aria-label="Summary sections"
          className="mb-6"
        />
      ) : null}

      {/*
        The retiring client made the body unselectable for everyone but an
        admin, which is the only copy protection the material has. Kept, and
        asked of the backend's own answer rather than a role string.
      */}
      <div className={cn(!isPlatformAdmin(session) && "select-none")}>
        {showTabs ? (
          <>
            <div className={tab === "clinical" ? "block" : "hidden"}>
              <ClinicalSections sections={sections} />
            </div>
            <div className={tab === "psychosocial" ? "block" : "hidden"}>
              <PsychosocialSections aspects={aspects} />
            </div>
          </>
        ) : body ? (
          <div className={t.b2cProseMeasureWide}>
            <Prose content={body} />
          </div>
        ) : (
          <p className={t.b2cBodyTextMuted}>This summary has no content yet.</p>
        )}
      </div>

      {playing ? (
        <Modal width="700px" height="fit-content" onClose={() => setPlaying(false)} title={item.title}>
          <SummaryPodcast item={item} />
        </Modal>
      ) : null}
    </div>
  );
}

/**
 * The playlist is every other summary that has audio, as it was before — the
 * point of the player is that one episode runs into the next. It is loaded
 * when the modal opens rather than beside the summary, so reading a summary
 * costs one request.
 */
function SummaryPodcast({ item }: { item: MediaItem }) {
  const { code: examCode } = useCurrentExam();
  const state = useAsync((signal) => listAllMedia("summary", signal, examCode), [examCode]);
  const [index, setIndex] = useState<number | null>(null);

  const withAudio = (state.data ?? []).filter((entry) => podcastUrl(entry) !== null);
  const episodes: Episode[] =
    withAudio.length > 0
      ? withAudio.map((entry) => ({ id: entry.id, title: entry.title, url: podcastUrl(entry) }))
      : [{ id: item.id, title: item.title, url: podcastUrl(item) }];

  const current = index ?? Math.max(0, episodes.findIndex((entry) => entry.id === item.id));

  if (state.loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Spinner />
      </div>
    );
  }

  return <PodcastPlayer episodes={episodes} index={current} onIndexChange={setIndex} />;
}
