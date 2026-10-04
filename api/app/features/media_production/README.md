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
  (`service_reads`, `with_review`), and `slide-scripts/tools/publish_deck.py` refuses to
  publish a row that still has it. Sources and evidence never reach learners.

## Routes
| Method | Path | Kind |
|--------|------|------|
| POST | `/api/v1/media/{id}/generate-podcast` | `summary` → `content.podcast_url` |
| POST | `/api/v1/media/{id}/regenerate-av` | `slide_deck` → TTS + video → `final_video_url` |
| POST | `/api/v1/media/{id}/generate-audio` | `podcast` → `content.audio_url` |
| POST | `/api/v1/media/{id}/check-facts` | `slide_deck`, `summary`, `podcast` → `content.review.facts` |
| POST | `/api/v1/media/{id}/write-script` | same kinds, body `{rewrite}` → narration or script, and `content.review.script` |

## The order of work

```
check-facts   -> check_media_facts   status checking_facts, then back to what it was
write-script  -> write_media_script  status writing_script, then awaiting_review
voicing route -> the three jobs below, refused unless the script is the one that was checked
```

- **Fact check** (`fact_check.py`): one model call lists the checkable clinical claims (60 at
  most). Each is put to Clinical Buddy's guideline library; only a claim the library does not
  support goes on to Clinical Buddy's web search. Verdicts: `supported`, `contradicted`,
  `not_found`, `conflict` (library and web disagree), `not_checked` (neither could be asked).
- **Script check** (`script_check.py`): writes whatever is not yet written (a deck's narration
  and framing, or a dialogue), then a second model reads every line against the material it
  was written from (Claude first, o3 second: the reverse of the writer). Lines written in the
  same run are corrected and re-read, twice at most; a line a person wrote or edited is only
  flagged. Flags: `name`, `number`, `logic`, `unsourced`, `story`, `rule`, `length`.
  `rewrite: true` discards the stored narration or script and writes it again.
- A failure is kept in `content.review.error` (`step`, `message`) with status `failed`.

Limits worth knowing: write-script on a published item rewrites its stored narration and
leaves it `awaiting_review` until it is voiced again; `media` refuses to save edits to a
published item, so accepting a correction applies to drafts; `scripts/regenerate_slides.py`
and `scripts/regenerate_podcasts.py` call the pipeline directly and are not gated.

## Jobs
| Task | Queue | Notes |
|------|-------|-------|
| `produce_summary_podcast` | `media` | Script + TTS for a summary |
| `regenerate_slide_av` | `media` | Slide video: ElevenLabs voice (Ben, or Michelle when the deck's content has `"presenter": "Michelle"`), Pillow frames, ffmpeg |
| `produce_podcast_audio` | `media` | Audio-only podcast |
| `check_media_facts` | `media` | Claims against the guideline library, then the web. No text changed |
| `write_media_script` | `media` | Narration or dialogue, then the second read. No ElevenLabs call |

Podcasts are voiced by ElevenLabs Eleven v4 (text-to-dialogue). Regenerate them all with
`poetry run python scripts/regenerate_podcasts.py --help`.

Run `make worker` beside `make start`. **ffmpeg** must be on `PATH` for slide video.

## Cross-slice dependencies
- **`media`**: reads and updates the media row and `content` payload.
- **`tutor_memory`** (`service_search.guideline_index`, `guideline_web`): Clinical Buddy's
  retrieve and web-search APIs, for the fact check. Unconfigured means "not checked", never an error.
- **`core.settings`**: model and AV keys (`OPENAI_API_KEY`, `ELEVENLABS_API_KEY` and voice ids, AWS S3).

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
