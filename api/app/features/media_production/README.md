# media_production

## Purpose
Async audio and video production for published study material (B2C parity): summary
podcasts, slide-deck AV, and standalone podcast audio. Platform admins trigger work
through `media` routes; this slice enqueues procrastinate jobs and updates the
parent `media` row's `content` JSON when generation finishes or fails.

## Aggregates & invariants
No tables of its own. Work is keyed by a `media` aggregate id.

- Only platform admins may start production (enforced on the HTTP routes in this slice).
- Enqueue and `content.status` transition happen in one transaction so a job is never
  orphaned without a `generating_*` status.
- On worker failure, `content.status` becomes `failed`; the admin re-runs the POST after
  fixing configuration or content.
- **Nothing is voiced unread.** The three voicing routes refuse `script_not_checked` (409)
  unless the lines they would speak (`script_check.spoken_lines`) are exactly the lines stored
  in `content.review.script.lines` by the last script check. Editing one line after the check
  means checking again, which costs no voice credits.
- **The fact check never changes the material.** It stores verdicts, evidence and suggested
  replacements; a person accepts one in the staff screen and saves.
- **`content.review` is staff-only.** `media` strips it from every learner read
  (`service_reads`, `with_review`). `slide-scripts/tools/publish_deck.py` carries it to the
  platform rows, so staff see what was checked, and never writes it to Firestore. Sources and
  evidence never reach learners.

## Routes
| Method | Path | Kind |
|--------|------|------|
| POST | `/api/v1/media/{id}/generate-podcast` | `summary` → `content.podcast_url` |
| POST | `/api/v1/media/{id}/regenerate-av` | `slide_deck` → TTS + video → `final_video_url` |
| POST | `/api/v1/media/{id}/generate-audio` | `podcast` → `content.audio_url` |
| POST | `/api/v1/media/{id}/check-facts` | `slide_deck`, `summary`, `podcast` → `content.review.facts` |
| POST | `/api/v1/media/{id}/write-script` | same kinds, body `{rewrite}` → narration or script, and `content.review.script` |
| POST | `/api/v1/media/{id}/produce`, `/stop-produce` | `slide_deck`, `summary`, `podcast`, body `{brief}` (a topic, notes or a pasted case) → the agent run below |
| POST | `/api/v1/platform/stations/{id}/versions/{n}/produce`, `/stop-produce` | a platform station's draft version → its `review` |

## The order of work

```
check-facts   -> check_media_facts   status checking_facts, then back to what it was
write-script  -> write_media_script  status writing_script, then awaiting_review
PATCH /media/{id} -> write_media_script  only when the save moved what a checked script was written from
voicing route -> the three jobs below, refused unless the script is the one that was checked
```

- **Fact check** (`service_facts.py`, which `stations` uses too): one model call lists the checkable clinical claims (60 at
  most). Each is put to Clinical Buddy's guideline library and its web search at once, and each
  source's own verdict is kept in `evidence`, labelled `guideline` or `web` with Clinical
  Buddy's reliability and source type. Verdicts: `supported`, `contradicted`,
  `not_found`, `conflict` (library and web disagree), `not_checked` (neither could be asked).
- **Script check** (`script_check.py`): writes whatever is not yet written (a deck's narration
  and framing, or a dialogue), then a second model reads every line against the material it
  was written from (Claude first, gpt-6.1-sol second: the reverse of the writer). Lines written in the
  same run are corrected and re-read, twice at most; a line a person wrote or edited is only
  flagged. Flags: `name`, `number`, `logic`, `unsourced`, `story`, `rule`, `length`.
  `rewrite: true` discards the stored narration or script and writes it again.
- A failure is kept in `content.review.error` (`step`, `message`) with status `failed`.

Limits worth knowing: write-script on a published item rewrites its stored narration and
leaves it `awaiting_review` until it is voiced again; `media` refuses to save edits to a
published item, so accepting a correction applies to drafts; `scripts/regenerate_slides.py`
and `scripts/regenerate_podcasts.py` call the pipeline directly and are not gated.

## The producing line (Produce)

One button runs a fixed line, the same order a person follows by hand. Code decides every step,
each stage runs once and nothing goes back; the model (`agent_loop.py`, OpenAI `PRODUCE_MODEL`)
is only asked narrow questions, each answered with one tool call. `produce.py` holds the line;
`service_produce.py` starts, stops, saves and takes over runs.

1. Draft, to the deck shape (15 to 17 slides, a varied opener, The Twist, telephone never video,
   only the diagnosis and management taken from a pasted case).
2. Decks: pictures (bundled library first, else a Commons search picked from a contact sheet,
   one retry), at the same time as one fact check of the draft.
3. Each contradicted or conflicting claim is ruled on (accept with exact words, or dismiss with a
   reason) in parallel, applied in order. A ruling whose words are gone is left for staff.
4. Decks, summaries and podcasts: the script is written and read, then `script_check.lint` and the
   reader's issues go to one edits question. Only edits that hit exactly one place and drop no
   audio tag are applied, then the script is checked again. At most two rounds; asides stay.
5. The hand-over (`review.run.summary`, `open`) is built by code: twists for sign-off, every
   correction and dismissal, what is left, slides without a picture.

A station runs steps 1, 3 and 5. The run stops at `awaiting_review`; voicing stays a person's
click. Every step saves the working copy and `review.run` (`steps`, `open`, `tokens`,
`heartbeat_at`) and publishes `media.updated` or `station.updated`; Produce on a run whose
heartbeat is 15 minutes old takes it over from the saved copy. A station's working copy is its
version's content plus `review` and `status`; while it is `producing` the version cannot be edited
or checked. Searched pictures are stored under `teaching_videos/sca/pictures/` in the bucket;
bundled ones are saved as `images/<name>`.

## Jobs
| Task | Queue | Notes |
|------|-------|-------|
| `produce_summary_podcast` | `media` | Script + TTS for a summary |
| `regenerate_slide_av` | `media` | Slide video: ElevenLabs voice (Ben, or Michelle when the deck's content has `"presenter": "Michelle"`), Pillow frames, ffmpeg |
| `produce_podcast_audio` | `media` | Audio-only podcast |
| `check_media_facts` | `media` | Claims against the guideline library and the web, side by side. No text changed |
| `write_media_script` | `media` | Narration or dialogue, then the second read. No ElevenLabs call |
| `produce_media`, `produce_station` | `produce` | The producing line. No ElevenLabs call |

Podcasts are voiced by ElevenLabs Eleven v4 (text-to-dialogue). Regenerate them all with
`poetry run python scripts/regenerate_podcasts.py --help`.

Run `make worker` beside `make start`. **ffmpeg** must be on `PATH` for slide video.

## Cross-slice dependencies
- **`media`**: reads and updates the media row and `content` payload.
- **`tutor_memory`** (`service_search.guideline_index`, `guideline_web`): Clinical Buddy's
  retrieve and web-search APIs, for the fact check. Unconfigured means "not checked", never an error.
- **`core.settings`**: model and AV keys (`OPENAI_API_KEY`, `ELEVENLABS_API_KEY` and voice ids, AWS S3).

## Files in the bucket
Every upload goes through `s3.upload_args(key)`: a real `ContentType` for known extensions
(inline, so a browser plays it) and `attachment` / `octet-stream` for anything else. Stored links are
the raw `https://<bucket>.s3.<region>.amazonaws.com/<key>`; `service_storage.sign_urls(value, prefixes=...)` turns
each link under the caller's folders into a two-hour signed link on read (media: `teaching_videos/<exam>/`, `podcasts/<exam>/`;
a station: its own older `stations/<id>/` folder and the `station_images/<exam>/` folders, where new uploads land, because authors write that content; every host spelling of
our bucket is matched, keys decode with `unquote_plus`), and withholds the link (empty string, logged once)
when signing is impossible, and the client is pinned to the regional
endpoint so the signed host matches the stored one and the web's `media-src`. Signing is local, so
it works with the bucket fully private (`osceguide-platform`; `core.bucket_layout` names every folder).
Deck pictures are signed like the decks. A link on the old `osceguide` bucket is never signed here;
`scripts/move_bucket_links.py` rewrites it. `tests/guards/test_media_links_are_signed.py` fails when a new file builds a bucket link.

## Local setup

From `api`, copy AV keys from the B2C `.env`:

```bash
poetry run python scripts/sync_av_env_from_b2c.py
```

Slide video: `slide_narration.py` writes Ben's words per slide moment and plans the talk
(section cards, three takeaways, sign-off), `slide_voice.py` voices each line, `slide_scenes.py`
draws the frames and `slide_av.py` times them and pipes them to ffmpeg. Re-render decks with
`poetry run python scripts/regenerate_slides.py --help`. Bundled assets:
`assets/slides/images/bg.png` (the logo is cut from it), `assets/fonts/Poppins-*.ttf`. Override
fonts with `MEDIA_AV_FONT_DIR` if needed.
