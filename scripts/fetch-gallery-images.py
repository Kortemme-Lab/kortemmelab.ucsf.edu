#!/usr/bin/env python3
"""Download the slideshow images wget could not see.

Weebly renders gallery/slideshow photos from a JavaScript payload
(`wSlideshow.render({... images:[{url:...}] ...})`) rather than <img> tags, so
a crawler never discovers them. This parses those payloads out of the mirrored
pages and fetches each image at both the size the slideshow displays and the
`_orig` full-resolution original, which is the one worth rebuilding around.

Idempotent: files already present are skipped.
"""
import json, os, re, sys, time, urllib.error, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
BASE = "https://kortemmelab.ucsf.edu/uploads/"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def slideshow_images(site):
    """Yield (page, url) for every image in a wSlideshow payload."""
    for fn in sorted(os.listdir(site)):
        if not fn.endswith(".html"):
            continue
        raw = open(os.path.join(site, fn), encoding="utf-8",
                   errors="replace").read()
        for m in re.finditer(r"images:\s*(\[\{.*?\}\])", raw, re.S):
            try:
                for im in json.loads(m.group(1)):
                    if im.get("url"):
                        yield fn, im["url"]
            except json.JSONDecodeError:
                continue


def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as fh:
        fh.write(r.read())
    return os.path.getsize(dest)


def main():
    if not os.path.isdir(os.path.join(SITE, "uploads")):
        print("site is already tidied -- gallery photos live in site/images/; nothing to fetch")
        return
    wanted = []
    for _, u in slideshow_images(SITE):
        stem, ext = os.path.splitext(u)
        for variant in (u, f"{stem}_orig{ext}"):
            if variant not in wanted:
                wanted.append(variant)

    got = skipped = failed = 0
    total_bytes = 0
    for u in wanted:
        dest = os.path.join(SITE, "uploads", u)
        if os.path.exists(dest):
            skipped += 1
            continue
        try:
            total_bytes += fetch(BASE + u, dest)
            got += 1
            time.sleep(0.3)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            failed += 1
            print(f"  FAILED {u}: {e}", file=sys.stderr)

    print(f"downloaded {got}, already present {skipped}, failed {failed} "
          f"({total_bytes / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
