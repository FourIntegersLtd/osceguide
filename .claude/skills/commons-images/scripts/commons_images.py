#!/usr/bin/env python3
"""Find free-to-use Wikimedia Commons images to sit beside the images already in station documents.

Stdlib only, except `extract --from-firestore`, which runs from api/ under `poetry run`. Read-only against Firestore and Commons; never deletes or rewrites existing images.

    extract  --export stations.json | --from-firestore   -> work/existing.json
    search   --queries work/queries.json                  -> work/candidates.json
    fetch    --approved work/approved.json                -> work/commons/<station>/<file> + manifest.json
    report                                                -> work/report.html + ATTRIBUTION.md
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "osceguide-commons-images/1.0 (fourintegers@gmail.com)"
IMAGE_URL = re.compile(r"^https?://\S+?(\.(jpe?g|png|gif|webp|svg|tiff?)(\?\S*)?$|firebasestorage\.googleapis\.com/\S+|storage\.googleapis\.com/\S+)", re.I)
TITLE_KEYS = ("station_name", "clinical_scenario_title", "title", "station_title", "name", "topic", "diagnosis", "condition", "scenario_title", "case_title")

# Licences that allow commercial use. Anything else is rejected.
ALLOWED = (
    re.compile(r"^cc0"),
    re.compile(r"^public domain"),
    re.compile(r"^pd\b|^pd-"),
    re.compile(r"^cc[ -]by[ -](\d|sa[ -]\d)"),
    re.compile(r"^cc[ -]by$"),
    re.compile(r"^cc[ -]by[ -]sa$"),
)
FORBIDDEN_WORDS = ("nc", "nd", "noncommercial", "non-commercial", "noderivs", "fair use", "gfdl only")
# Categories / templates that mean the licence is disputed or the file is up for deletion.
RED_FLAGS = re.compile(
    r"deletion request|copyright violation|copyvio|no permission|no source|no license|"
    r"license review needed|unknown copyright|possible copyright|speedy deletion|disputed",
    re.I,
)


def _get(params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "format": "json", "formatversion": "2"}
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code < 500 or attempt == 3:
                raise
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    return {}


def _strip_html(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


# ---------- extract ----------

def _walk(node: Any, path: str, found: list[dict[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            _walk(value, f"{path}.{key}" if path else str(key), found)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _walk(value, f"{path}[{i}]", found)
    elif isinstance(node, str) and IMAGE_URL.match(node.strip()):
        found.append({"field": path, "url": node.strip()})


def _title(doc: dict[str, Any]) -> str:
    for key in TITLE_KEYS:
        value = doc.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return str(doc.get("id", "untitled"))


def _load_firestore(product: str, api_dir: Path) -> list[dict[str, Any]]:
    sys.path.insert(0, str(api_dir))
    # The .env files import_b2c_stations.py loads; b2c_firestore turns them into credentials.
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(api_dir / ".env")
    load_dotenv(api_dir.resolve().parent / "b2c-api" / ".env", override=False)
    from app.migration.b2c_station_sources import stream_b2c_station_documents  # type: ignore

    return stream_b2c_station_documents(products=[product])


def cmd_extract(args: argparse.Namespace) -> None:
    if args.export:
        docs = json.loads(Path(args.export).read_text(encoding="utf-8"))
        if args.app_type:
            docs = [d for d in docs if d.get("app_type", args.app_type) == args.app_type]
    else:
        docs = _load_firestore(args.app_type, Path(args.api_dir))
    out = []
    for doc in docs:
        found: list[dict[str, str]] = []
        _walk(doc, "", found)
        if found or args.include_without_images:
            out.append({"station_id": str(doc.get("id")), "title": _title(doc), "existing": found})
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    (work / "existing.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    images = sum(len(s["existing"]) for s in out)
    print(f"stations read: {len(docs)}  with images: {sum(1 for s in out if s['existing'])}  images: {images}")
    print(f"wrote {work / 'existing.json'}")


# ---------- licence check ----------

def licence_verdict(meta: dict[str, Any], categories: list[str], templates: list[str]) -> tuple[bool, list[str]]:
    """(ok, reasons). Two independent checks: the licence metadata, then the page's categories/templates."""
    reasons: list[str] = []
    short = _strip_html(meta.get("LicenseShortName", {}).get("value", "")).lower()
    code = _strip_html(meta.get("License", {}).get("value", "")).lower()
    usage = _strip_html(meta.get("UsageTerms", {}).get("value", "")).lower()
    restrictions = _strip_html(meta.get("Restrictions", {}).get("value", ""))
    non_free = _strip_html(meta.get("NonFree", {}).get("value", "")).lower()

    name = code or short
    if not name:
        reasons.append("no licence in metadata")
    elif not any(p.search(name) for p in ALLOWED) and not any(p.search(short) for p in ALLOWED):
        reasons.append(f"licence not on allow-list: {short or code}")
    tokens = set(re.split(r"[\s\-_/]+", f"{code} {short} {usage}"))
    if any(w in tokens or (" " in w and w in f"{code} {short} {usage}") for w in FORBIDDEN_WORDS):
        reasons.append(f"non-commercial or no-derivatives terms: {short or code}")
    if non_free in ("true", "1"):
        reasons.append("marked NonFree")
    if restrictions:
        reasons.append(f"restrictions: {restrictions} (needs human review)")
    if not _strip_html(meta.get("Artist", {}).get("value", "")) and not name.startswith(("pd", "public domain", "cc0")):
        reasons.append("no author for required attribution")
    for item in categories + templates:
        if RED_FLAGS.search(item):
            reasons.append(f"red flag on file page: {item}")
    return (not reasons, reasons)


# ---------- search ----------

IMAGEINFO = {"prop": "imageinfo|categories|templates", "iiprop": "url|extmetadata|mime|size",
             "iiurlwidth": "640", "cllimit": "max", "tllimit": "max"}


def _page_to_candidate(page: dict[str, Any]) -> dict[str, Any]:
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata", {})
    ok, reasons = licence_verdict(meta, [c["title"] for c in page.get("categories", [])],
                                  [t["title"] for t in page.get("templates", [])])
    licence = _strip_html(meta.get("LicenseShortName", {}).get("value", ""))
    return {
        "file": page["title"],
        "page_url": info.get("descriptionurl"),
        "original_url": info.get("url"),
        "thumb_url": info.get("thumburl"),
        "mime": info.get("mime"),
        "width": info.get("width"),
        "height": info.get("height"),
        "description": _strip_html(meta.get("ImageDescription", {}).get("value", ""))[:300],
        "author": _strip_html(meta.get("Artist", {}).get("value", "")),
        "credit": _strip_html(meta.get("Credit", {}).get("value", ""))[:200],
        "licence": licence,
        "licence_url": meta.get("LicenseUrl", {}).get("value", ""),
        "attribution_required": meta.get("AttributionRequired", {}).get("value", "") == "true",
        "share_alike": "sa" in re.split(r"[\s\-]+", licence.lower()),
        "licence_ok": ok,
        "licence_reasons": reasons,
    }


def _lookup(titles: list[str]) -> list[dict[str, Any]]:
    """Checked candidates for the given File: titles that exist on Commons, in Commons' order."""
    data = _get({"action": "query", "titles": "|".join(titles), **IMAGEINFO})
    pages = data.get("query", {}).get("pages", [])
    return [_page_to_candidate(pg) for pg in pages if not (pg.get("missing") or pg.get("invalid"))]


def _search(query: str, limit: int) -> list[dict[str, Any]]:
    data = _get({"action": "query", "generator": "search", "gsrsearch": f"{query} filetype:bitmap",
                 "gsrnamespace": "6", "gsrlimit": str(limit), **IMAGEINFO})
    return [_page_to_candidate(page) for page in data.get("query", {}).get("pages", [])]


def _trace_existing(url: str) -> dict[str, Any] | None:
    """The Commons file an existing image was copied from, matched by filename, if there is one."""
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1].split("?", 1)[0])
    stem, _, ext = name.rpartition(".")
    if not stem or "|" in name:
        return None
    # Copies often change the extension's case (Kneeffusion.JPG on Commons, .jpg in S3).
    found = _lookup(list(dict.fromkeys(f"File:{stem}.{e}" for e in (ext, ext.upper(), ext.lower()))))
    return found[0] if found else None


def cmd_search(args: argparse.Namespace) -> None:
    work = Path(args.work)
    queries = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    existing = {s["station_id"]: s for s in json.loads((work / "existing.json").read_text(encoding="utf-8"))}
    out = []
    for station_id, terms in queries.items():
        seen, cands = set(), []
        for term in terms if isinstance(terms, list) else [terms]:
            for c in _search(term, args.limit):
                if c["file"] not in seen:
                    seen.add(c["file"])
                    c["query"] = term
                    cands.append(c)
            time.sleep(0.5)
        station = existing.get(station_id, {"station_id": station_id, "title": station_id, "existing": []})
        for x in station["existing"]:
            x["commons_source"] = _trace_existing(x["url"])
            time.sleep(0.5)
        out.append({**station, "candidates": cands})
        passed = sum(1 for c in cands if c["licence_ok"])
        print(f"{station_id}: {len(cands)} candidates, {passed} pass licence check")
    (work / "candidates.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {work / 'candidates.json'}")


# ---------- fetch ----------

def _safe_name(file_title: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", file_title.removeprefix("File:"))[:150]


def load_manifest(work: Path) -> list[dict[str, Any]]:
    """The fetched images (`fetch` writes it; `publish_images.py s3` adds each `s3_url`)."""
    path = work / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save_manifest(work: Path, manifest: list[dict[str, Any]]) -> None:
    (work / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_fetch(args: argparse.Namespace) -> None:
    """Re-check each approved file's licence live (second pass), then download it."""
    work = Path(args.work)
    approved: dict[str, list[str]] = json.loads(Path(args.approved).read_text(encoding="utf-8"))
    manifest = []
    for station_id, files in approved.items():
        for file_title in files:
            found = _lookup([file_title])
            if not found:
                print(f"SKIP {file_title}: not on Commons")
                continue
            match = found[0]
            if not match.get("licence_ok"):
                print(f"SKIP {file_title}: {match.get('licence_reasons')}")
                continue
            dest = work / "commons" / station_id / _safe_name(file_title)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                req = urllib.request.Request(match["original_url"], headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    dest.write_bytes(resp.read())
                time.sleep(0.5)
            manifest.append({"station_id": station_id, "local_path": str(dest.relative_to(work)), **match,
                             "attribution": attribution(match)})
            print(f"OK   {station_id}: {file_title} ({match['licence']})")
    save_manifest(work, manifest)
    print(f"wrote {work / 'manifest.json'} ({len(manifest)} files)")


def attribution(c: dict[str, Any]) -> str:
    author = c.get("author") or "Unknown author"
    return f'"{c["file"].removeprefix("File:")}" by {author}, {c.get("licence")}' + \
        (f' ({c["licence_url"]})' if c.get("licence_url") else "") + f', via Wikimedia Commons: {c.get("page_url")}'


# ---------- report ----------

def _existing_status(x: dict[str, Any]) -> str:
    src = x.get("commons_source")
    if not src:
        return '<span class="warn">licence unknown — check source</span>'
    verdict = "ok" if src["licence_ok"] else "bad"
    return (f'<span class="{verdict}">same filename on Commons: <a href="{html.escape(src["page_url"] or "")}">'
            f'<b>{html.escape(src["licence"] or "?")}</b></a>, by {html.escape(src["author"][:60] or "?")} — '
            f'confirm it is the same picture</span>')


def cmd_report(args: argparse.Namespace) -> None:
    work = Path(args.work)
    stations = json.loads((work / "candidates.json").read_text(encoding="utf-8"))
    manifest = load_manifest(work)
    fetched = {(m["station_id"], m["file"]) for m in manifest}
    e = html.escape
    rows = []
    for s in stations:
        left = "".join(
            f'<figure><img src="{e(x["url"])}" loading="lazy"><figcaption>{e(x["field"])}<br>{_existing_status(x)}'
            f'</figcaption></figure>' for x in s["existing"]
        ) or "<p class='muted'>no existing image</p>"
        right = []
        for c in s["candidates"]:
            if not c["licence_ok"] and not args.show_rejected:
                continue
            tag = "ok" if c["licence_ok"] else "bad"
            status = "downloaded" if (s["station_id"], c["file"]) in fetched else ("passes" if c["licence_ok"] else "rejected")
            reasons = "" if c["licence_ok"] else "<br>" + e("; ".join(c["licence_reasons"]))
            sa = " · share-alike" if c.get("share_alike") else ""
            right.append(
                f'<figure class="{tag}"><a href="{e(c["page_url"] or "")}"><img src="{e(c["thumb_url"] or "")}" loading="lazy"></a>'
                f'<figcaption><b>{e(c["licence"] or "?")}</b>{sa} · {status}<br>{e(c["file"])}<br>'
                f'by {e(c["author"][:80] or "?")}{reasons}</figcaption></figure>'
            )
        rows.append(f'<section><h2>{e(s["title"])} <small>{e(s["station_id"])}</small></h2>'
                    f'<div class="cols"><div><h3>Existing</h3>{left}</div>'
                    f'<div><h3>Wikimedia Commons</h3>{"".join(right) or "<p class=muted>none passed</p>"}</div></div></section>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Station images</title><style>
:root{{--bg:#fff;--fg:#1a1a1a;--muted:#666;--ok:#1b7f3b;--bad:#b3261e;--line:#ddd}}
@media (prefers-color-scheme:dark){{:root{{--bg:#141414;--fg:#eee;--muted:#999;--ok:#5bd17f;--bad:#ff8a80;--line:#333}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.4 system-ui;margin:0 auto;max-width:1200px;padding:16px}}
.cols{{display:grid;grid-template-columns:1fr 2fr;gap:16px}}@media(max-width:700px){{.cols{{grid-template-columns:1fr}}}}
section{{border-top:1px solid var(--line);padding:12px 0}}figure{{display:inline-block;width:200px;margin:4px;vertical-align:top}}
img{{width:100%;background:#000;border-radius:4px}}figcaption{{font-size:12px;word-break:break-word}}
.ok b,.ok{{color:var(--ok)}}.bad b,.warn{{color:var(--bad)}}.muted,small{{color:var(--muted)}}
</style></head><body><h1>Station images: existing vs Wikimedia Commons</h1>
<p class="muted">Green = licence allows commercial use (two checks passed). Every Commons image needs the attribution in ATTRIBUTION.md shown in the app. Existing images are untouched.</p>
{''.join(rows)}</body></html>"""
    (work / "report.html").write_text(page, encoding="utf-8")
    if manifest:
        lines = ["# Image attribution (Wikimedia Commons)", "",
                 "Show these credits in the app (e.g. an image credits screen or under each image).", ""]
        for m in manifest:
            lines.append(f"- `{m['local_path']}` — {m['attribution']}" + (" — **share-alike**: adaptations must use the same licence" if m.get("share_alike") else ""))
        (work / "ATTRIBUTION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {work / 'report.html'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", default="commons-work", help="output folder (default ./commons-work)")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract")
    src = e.add_mutually_exclusive_group(required=True)
    src.add_argument("--export", help="stations.json export (JSON array of documents)")
    src.add_argument("--from-firestore", action="store_true", help="read live (read-only) via osceguide/api")
    e.add_argument("--app-type", default="ortho", help="sca | plab | casc | ortho (default ortho)")
    e.add_argument("--api-dir", default="api", help="path to osceguide/api for --from-firestore")
    e.add_argument("--include-without-images", action="store_true")
    s = sub.add_parser("search")
    s.add_argument("--queries", required=True, help='JSON {"station_id": ["query", ...]}')
    s.add_argument("--limit", type=int, default=12)
    f = sub.add_parser("fetch")
    f.add_argument("--approved", required=True, help='JSON {"station_id": ["File:...", ...]}')
    r = sub.add_parser("report")
    r.add_argument("--show-rejected", action="store_true")
    args = p.parse_args()
    {"extract": cmd_extract, "search": cmd_search, "fetch": cmd_fetch, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    main()
