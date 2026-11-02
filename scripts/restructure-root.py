#!/usr/bin/env python3
"""Flatten the wget host-directory layout into a single deployable web root.

wget produces archive/site/<host>/... per host, so index.html sits one level down and
reaches its Weebly CDN assets via `../cdn11.editmysite.com/...`. That renders
over file:// but 404s the moment the site is served from a single web root
(a local server, GitHub Pages, any static host).

After this script, archive/site/ IS the web root: the 101 pages sit at the top level
and third-party assets live under archive/site/_cdn/<host>/. Every reference is
recomputed relative to the file that holds it, so nesting depth doesn't matter.

Idempotent: running it again is a no-op.
"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "archive", "site")
MAIN_HOST = "kortemmelab.ucsf.edu"
CDN_HOSTS = ["cdn11.editmysite.com", "cdn2.editmysite.com", "cdn.mathjax.org"]
CDN_DIR = "_cdn"
TEXT_EXT = {".html", ".htm", ".css", ".js"}

REF_RE = re.compile(
    r"(?:\.\./)+(" + "|".join(re.escape(h) for h in CDN_HOSTS) + r")/")


def main():
    main_dir = os.path.join(SITE, MAIN_HOST)
    cdn_root = os.path.join(SITE, CDN_DIR)

    if not os.path.isdir(main_dir):
        print("already restructured (archive/site/ is the web root)")
        return

    # 1. third-party hosts -> archive/site/_cdn/<host>/  (kept as siblings, so the
    #    few intra-CDN `../<other-cdn>/` refs stay correct untouched)
    os.makedirs(cdn_root, exist_ok=True)
    for host in CDN_HOSTS:
        src = os.path.join(SITE, host)
        if os.path.isdir(src):
            shutil.move(src, os.path.join(cdn_root, host))

    # 2. main host contents -> archive/site/ root
    for entry in os.listdir(main_dir):
        shutil.move(os.path.join(main_dir, entry), os.path.join(SITE, entry))
    os.rmdir(main_dir)

    # 3. recompute every CDN reference relative to the holding file
    edited = 0
    for dirpath, dirnames, filenames in os.walk(SITE):
        if os.path.relpath(dirpath, SITE).split(os.sep)[0] == CDN_DIR:
            continue  # intra-CDN refs are already correct
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                text = fh.read()

            def fix(m):
                host = m.group(1)
                target = os.path.join(cdn_root, host)
                rel = os.path.relpath(target, dirpath).replace(os.sep, "/")
                return rel + "/"

            new_text = REF_RE.sub(fix, text)
            if new_text != text:
                with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new_text)
                edited += 1

    print(f"archive/site/ is now the web root; rewrote CDN refs in {edited} files")


if __name__ == "__main__":
    main()
