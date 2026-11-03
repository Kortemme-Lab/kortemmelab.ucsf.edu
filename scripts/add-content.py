#!/usr/bin/env python3
"""Add a news item, or photos for the gallery.

    python3 scripts/add-content.py news --month June --year 2025 --text "Colin receives tenure"
    python3 scripts/add-content.py news --month June --year 2025 --text "…" --link https://…
    python3 scripts/add-content.py photos --caption "Lab retreat 2026" ~/Downloads/a.jpg ~/Downloads/b.jpg

`news` adds one line to content/news.md, in date order (newest first, and
first among items from the same month).

`photos` adds photos at the top of the gallery (content/gallery.md), saved in
content/images/gallery/. Each is turned upright, scaled down to at most
1600 pixels, and saved as a JPEG **without its metadata**, so the camera's
GPS location and other details aren't published. The caption goes on the
first photo, as the gallery's captions do; every photo gets it as alt text.
This needs Pillow, the standard Python imaging library:
`python3 -m pip install pillow` (the workflow installs it on GitHub).

Both accept --dry-run (check, write nothing) and --report FILE (what was
found, as JSON, for .github/workflows/submission.yml). Run
scripts/build-site.py afterwards, or push: GitHub rebuilds the site.
"""
import argparse, datetime, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS = os.path.join(ROOT, "content", "news.md")
GALLERY = os.path.join(ROOT, "content", "gallery.md")
GALLERY_DIR = os.path.join(ROOT, "content", "images", "gallery")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
MAX_SIDE = 1600              # the gallery shows photos about 1000 px wide; this is sharp on retina screens
MAX_PHOTOS = 10
MAX_TEXT = {"news": 500, "caption": 300}


def md_text(s):
    """Plain text, safe inside the site's Markdown: one line, no stray markup."""
    s = re.sub(r"\s+", " ", s or "").strip()
    return re.sub(r"([\\`*_\[\]])", r"\\\1", s)


def slugify(s, words=6):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return "-".join(s.split("-")[:words]) or "photo"


def report_out(path, entry):
    if path:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([entry], fh, indent=2, ensure_ascii=False)


# --- news ------------------------------------------------------------------------------------
def news_key(month, year):
    return int(year) * 12 + MONTHS.index(month)


def add_news(month, year, text, link, dry_run, report_path):
    entry = {"kind": "news", "status": "ok", "problem": "", "notes": [], "changes": []}
    month = (month or "").strip().capitalize()
    year = (year or "").strip()
    problem = None
    if month not in MONTHS:
        problem = f"\"{month}\" isn't a month"
    elif not re.fullmatch(r"(19|20)\d{2}", year):
        problem = f"\"{year}\" isn't a year"
    elif int(year) > datetime.date.today().year + 1:
        problem = f"{year} is too far ahead"
    elif not (text or "").strip():
        problem = "the news item is empty"
    elif len(text.strip()) > MAX_TEXT["news"]:
        problem = f"the news item is over {MAX_TEXT['news']} characters; keep it to a sentence or two"
    elif link and not re.fullmatch(r"https?://\S+", link.strip()):
        problem = "the link should start with https://"
    if problem:
        entry.update(status="skipped", problem=problem)
        print(f"skipped: {problem}")
        return report_out(report_path, entry)

    body = md_text(text)
    if link:
        body = f"[{body}]({link.strip()})"
    line = f"- **{month} {year}** {body}"
    lines = open(NEWS, encoding="utf-8").read().split("\n")
    new_key = news_key(month, year)
    # before the first item that isn't newer; after the last item if all are
    at, last = None, None
    for i, ln in enumerate(lines):
        m = re.match(r"^- \*\*([A-Za-z]+) (\d{4})\*\*", ln)
        if not m or m.group(1) not in MONTHS:
            continue
        if news_key(m.group(1), m.group(2)) <= new_key:
            at = i
            break
        last = i
    if at is None:
        at = last + 1 if last is not None else len(lines)
    if any(ln.strip() == line for ln in lines):
        entry.update(status="skipped", problem="that news item is on the website already")
        print("skipped: already there")
        return report_out(report_path, entry)
    lines.insert(at, line)
    entry.update(date=f"{month} {year}", text=re.sub(r"\s+", " ", text).strip(), link=(link or "").strip(),
                 line=line, changes=[f"news for {month} {year}"])
    print(f"news: {line}")
    if not dry_run:
        with open(NEWS, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
    report_out(report_path, entry)


# --- photos ----------------------------------------------------------------------------------
def prepare_photo(path):
    """The photo upright, at most MAX_SIDE pixels, as JPEG bytes with no metadata; or a reason why not."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        sys.exit("Adding photos needs Pillow: python3 -m pip install pillow")
    try:
        with Image.open(path) as im:
            im.load()
            fmt = im.format
            im = ImageOps.exif_transpose(im)      # apply the camera's rotation, then drop its metadata
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                back = Image.new("RGB", im.size, "white")
                back.paste(im, mask=im.split()[-1])
                im = back
            else:
                im = im.convert("RGB")
            w, h = im.size
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=85, optimize=True, progressive=True)   # no exif= : nothing carried over
            return {"bytes": buf.getvalue(), "original": (w, h), "saved": im.size, "format": fmt}, None
    except Exception as e:
        return None, f"isn't a photo this can read ({e.__class__.__name__}); use a JPG or PNG"


def add_photos(paths, caption, dry_run, report_path):
    entry = {"kind": "gallery", "status": "ok", "problem": "", "notes": [], "changes": [], "photos": []}
    caption = re.sub(r"\s+", " ", caption or "").strip()
    if not paths:
        entry.update(status="skipped", problem="there are no photos to add")
    elif len(paths) > MAX_PHOTOS:
        entry.update(status="skipped", problem=f"that's {len(paths)} photos; please send at most {MAX_PHOTOS} at a time")
    elif len(caption) > MAX_TEXT["caption"]:
        entry.update(status="skipped", problem=f"the caption is over {MAX_TEXT['caption']} characters")
    if entry["status"] != "ok":
        print(f"skipped: {entry['problem']}")
        return report_out(report_path, entry)

    stem = f"{datetime.date.today():%Y-%m}-{slugify(caption) if caption else 'photo'}"
    ready = []
    for n, path in enumerate(paths, 1):
        got, problem = prepare_photo(path)
        if problem:
            entry["notes"].append(f"photo {n} {problem}; left out")
            continue
        k = len(ready) + 1                                              # numbered among the photos kept
        name, i = f"{stem}-{k}.jpg", 2
        while os.path.exists(os.path.join(GALLERY_DIR, name)):          # never overwrite a photo
            name, i = f"{stem}-{k}-{i}.jpg", i + 1
        if min(got["original"]) < 600:
            entry["notes"].append(f"photo {n} is only {got['original'][0]} × {got['original'][1]} pixels, so it may look blurry")
        ready.append((name, got))
        entry["photos"].append({"file": f"content/images/gallery/{name}",
                                "original": "×".join(map(str, got["original"])),
                                "saved": "×".join(map(str, got["saved"]))})
    if not ready:
        entry.update(status="skipped", problem="none of the photos could be read; use JPG or PNG files")
        print(f"skipped: {entry['problem']}")
        return report_out(report_path, entry)

    alt = md_text(caption)
    blocks = []
    for k, (name, _) in enumerate(ready):
        block = f"![{alt}](images/gallery/{name})"
        if k == 0 and caption:
            block += f"\n*{md_text(caption)}*"
        blocks.append(block)
    text = open(GALLERY, encoding="utf-8").read()
    m = re.search(r"(?m)^## Gallery.*\n\n", text)
    at = m.end() if m else text.index("\n---\n", 4) + 5
    text = text[:at] + "\n\n".join(blocks) + "\n\n" + text[at:]
    n = len(ready)
    entry.update(caption=caption, changes=[f"{n} photo{'s' * (n != 1)} added to the gallery"])
    print(f"gallery: {', '.join(name for name, _ in ready)}")
    if not dry_run:
        os.makedirs(GALLERY_DIR, exist_ok=True)
        for name, got in ready:
            with open(os.path.join(GALLERY_DIR, name), "wb") as fh:
                fh.write(got["bytes"])
        with open(GALLERY, "w", encoding="utf-8") as fh:
            fh.write(text)
    report_out(report_path, entry)


def main():
    ap = argparse.ArgumentParser(description="Add a news item, or photos for the gallery.")
    sub = ap.add_subparsers(dest="what", required=True)
    n = sub.add_parser("news", help="add a news item")
    n.add_argument("--month", required=True)
    n.add_argument("--year", required=True)
    n.add_argument("--text", required=True)
    n.add_argument("--link", default="")
    p = sub.add_parser("photos", help="add photos to the gallery")
    p.add_argument("files", nargs="*")
    p.add_argument("--caption", default="")
    for s in (n, p):
        s.add_argument("--dry-run", action="store_true", help="check, and write nothing")
        s.add_argument("--report", metavar="FILE", help="also write what was found as JSON")
    a = ap.parse_args()
    if a.what == "news":
        add_news(a.month, a.year, a.text, a.link, a.dry_run, a.report)
    else:
        add_photos([os.path.expanduser(f) for f in a.files], a.caption, a.dry_run, a.report)


if __name__ == "__main__":
    main()
