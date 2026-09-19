"use client";

import { useState } from "react";
import { HiOutlineHeart, HiOutlineMicrophone } from "react-icons/hi2";
import { LuPodcast, LuStethoscope } from "react-icons/lu";
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
import { useSession } from "@/foundation/session";
import { isPlatformAdmin } from "@/foundation/session";
import {
  bodyMarkdown,
  listAllMedia,
  podcastUrl,
  psychosocialAspects,
  summarySections,
  type MediaItem,
} from "@/capabilities/media/api";
import { ClinicalSections, PsychosocialSections } from "@/capabilities/media/SummarySections";
import { Prose } from "@/capabilities/media/Prose";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";

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
  const structured = sections.length > 0 || aspects.length > 0;
  const audio = podcastUrl(item);
  const body = bodyMarkdown(item);

  return (
    <div className="w-full text-left">
      <B2CPageHeader
        title={item.title}
        back={{ href: hrefFor("/library"), label: "Study material" }}
        className="mb-6 border-b-0 pb-0 sm:pb-0"
      />

      {structured || audio ? (
        <div className="mb-8 flex flex-col-reverse gap-4 md:flex-row md:items-center md:justify-between">
          {structured ? (
            <B2CSegmentedTabs
              items={[
                {
                  id: "clinical",
                  label: (
                    <span className="inline-flex items-center gap-2">
                      <LuStethoscope className="h-4 w-4" aria-hidden />
                      Clinical Management
                    </span>
                  ),
                },
                {
                  id: "psychosocial",
                  label: (
                    <span className="inline-flex items-center gap-2">
                      <HiOutlineHeart className="h-4 w-4" aria-hidden />
                      Psychosocial
                    </span>
                  ),
                },
              ]}
              value={tab}
              onChange={setTab}
              aria-label="Summary sections"
            />
          ) : (
            <span />
          )}

          {audio ? <ListenCard onListen={() => setPlaying(true)} /> : null}
        </div>
      ) : null}

      {/*
        The retiring client made the body unselectable for everyone but an
        admin, which is the only copy protection the material has. Kept, and
        asked of the backend's own answer rather than a role string.
      */}
      <div className={cn(!isPlatformAdmin(session) && "select-none")}>
        {structured ? (
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

function ListenCard({ onListen }: { onListen: () => void }) {
  return (
    <div className="w-full md:ml-4 md:w-auto">
      <div className="rounded-xl border border-osce-accent-muted bg-gradient-to-r from-osce-accent-muted to-osce-accent-subtle p-3 transition-all duration-300">
        <div className="flex items-center justify-between gap-3 md:justify-start">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-osce-accent to-osce-accent-hover">
              <LuPodcast className="h-4 w-4 text-white" aria-hidden />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-osce-body text-b2c-text-secondary">7-10 min audio</span>
              <span className="text-osce-caption text-b2c-text-muted">with Ben &amp; Michelle</span>
            </div>
          </div>
          <Button type="button" onClick={onListen} className="gap-2">
            <HiOutlineMicrophone className="h-3 w-3" aria-hidden />
            <span>Listen</span>
          </Button>
        </div>
      </div>
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
  const state = useAsync((signal) => listAllMedia("summary", signal), []);
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
