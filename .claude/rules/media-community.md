---
paths:
  - "api/app/features/{media,media_production,community,marketplace,peer_practice,cv}/**"
  - "api/scripts/{import_b2c_media,import_b2c_community,import_b2c_marketplace,regenerate_podcasts,regenerate_slides,copy_podcast_urls,sync_b2c_podcast_urls}.py"
  - "web/src/capabilities/{media,community,peer-practice,fact-check,staff-media,staff-moderation}/**"
---
# Media, community and peer practice: what to know

Owner: `content-owner` (staff queues `staff-console-owner`). Proof: `verify-content`.

- Social content is filtered by audience (ADR 0014): a like or read must respect it
  (`tests/security/test_community_like_audience.py`).
- Study media (slides, podcasts, summaries) is produced by background jobs in `media_production`
  and indexed for search; publishing reindexes (`test_media_publish_reindex_job`). Slide image paths
  are traversal-checked; uploads are content-sniffed (`tests/security`).
- Slide decks for teaching are made by the `slide-deck-author` agent through platform-api's staff
  media routes only; do not add side routes.
- A published deck carries `content.captions_vtt`, cut at publish from the per-slide timings the
  render stored (`media_production/captions.py`); a deck without timings gets none, and decks made
  before timings were stored stay uncaptioned until re-rendered. `scripts/sync_deck_topics_and_captions.py`
  backfills `topic` and captions (dry run by default). Decks are headed by `content.topic`, with the
  title beneath (`deckHeading`).
- A to Z and Podcasts read the whole catalogue (`useClientPagedCatalogue`); jump links are built from
  all of it, not the shown rows. One `useStudySearch` per page, passed down; a list that reloads
  stays mounted so the search box keeps focus.
- Marketplace: a claim is race-safe (`test_marketplace_claim_race`) and reminders are scheduled
- A slot's `status` is `available | claimed | cancelled` (a `Literal` on `PostRead`, so the generated web type is a union). `peer-practice/marketplace/copy.ts` `slotBadge` switches over it exhaustively; add a status in the api and the web type check fails there. "Expired" is an unclaimed slot in the past, never a status. A walkthrough account has no SCA entitlement here, so seed a cancelled slot by SQL to see it in the browser.
  jobs. Peer practice: queue pairing is race-safe, the accept handshake and recording have state
  over time, transcripts are diarised (`peer_practice/diariser.py`).
- Starting a peer room is `attempt-engine-owner`'s (`peer_practice/service_voice.py` is the join
  point; ask before changing it). Marking a peer session is not a mark.
- CV reading (`cv/`) sends a user's document to a model.
- Trial access to media is limited (`test_media_trial_access`); do not widen a read to fix a screen.
- Web: staff screens that act on this content live in `staff-media` and `staff-moderation`.
  Handles: `web/.claude/skills/verify/features/marketplace.md`.
- Community list narrowing (`mine`, `tag`, `exam_code`) is done in SQL and can only narrow the viewer's audience, never widen it. The discussion tab (`?tab=all|exam|questions|answers`, `compose=1`) and reply sort are pure functions in `web/.../community/discussionModel.ts`.
- A question has a `category` (`general`, `platform`, `skills`, `exam`; `domain.CATEGORIES`), validated server-side (`invalid_category`; an `exam` question must name its exam: `exam_required_for_category`). Free-text `tags` are its subtags. Replies take their question's category. The composer has no category or exam select: it posts the default category tagged with the current exam, and the Exam tab asks `exam_code` only (the category column and `?category` filter stay a valid API).
- The OSCE Guide assistant decides for itself, not by category: `ask` queues the job for every public question, and the model answers only from the help entries, else outputs `NO_REPLY` (`parse_reply` -> the drafter returns `None`: nothing posted, the job succeeds, logged at info). Only public questions nobody has answered when the job runs. `ask` defers job `reply_as_assistant` (`community/jobs.py`) for that one post in its own transaction (`defer_in_transaction`); there is no cron, no flag and no wait, so a reply comes promptly. It needs `OPENAI_API_KEY`: without it the queue row fails. It drafts from the help pack's FAQ (`assistant/service_community.py`) and posts a reply with `is_assistant=true` and `author_id` NULL (no fake user; `PostRead.author_id` is nullable). A failing draft (not `NO_REPLY`) fails the queue row (guard `STATE` entry), it is never swallowed. The persona is Athena (prompt: "You are Athena, the OSCE Guide assistant"; first person, no lists). On commit the job publishes `community_reply` `{post_id, reply_id}` to the asker's `/me/events` topic and `QuestionDetail` reloads the thread on it (no polling). The web label is `ASSISTANT_LABEL` ("Athena") and the reply is signed with `AthenaIdentity` inline. The Help dock stays text only on community.
- **Blogs are public and never locked.** `GET /media*` returns a blog's body to a signed-out reader (the public `/blogs` pages); every other kind stays gated by exam. Link a media item with `studyItemHref` (blogs go to `/blogs/<slug>`, outside the workspace, so skip `hrefFor`); the portal `/articles` routes only redirect.
- **The app shell scrolls an inner `overflow-auto` div, not the window.** `window.scrollTo`, `scrollY` and a window `scrollend` do nothing there; scroll the nearest `overflow-y` ancestor, and measure a sticky header by its stuck position (scroller top + its height), not its bottom at rest. Check any jump or scroll-spy in a browser (`web/src/capabilities/media/useJumpIndex.ts`).

## What a failure looks like here
- Content shown to an audience it is not for, or a narrowing filter that widens.
- A trial or locked reader gets gated media (only blogs are public).
- A race in a claim, pairing or handshake that lets two people take one slot, or one join a dead session.
- A published deck not reindexed, or missing its captions.
