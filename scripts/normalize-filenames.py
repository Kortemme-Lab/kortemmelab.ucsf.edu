#!/usr/bin/env python3
"""Normalize wget's query-string filenames in the mirror.

wget saves cache-busted assets as `main_style.css?1774157528.css` but rewrites
the HTML to point at `main_style.css%3F1774157528.css`. Browsers mostly cope,
but literal `?` in filenames breaks git, most static hosts, and any build step.

This renames every such file to its clean base name and rewrites all references
in the mirrored .html/.css/.js files to match. Where several cache-busted
variants share a base name, byte-identical ones collapse into a single file and
genuinely different ones get a `~2`, `~3` suffix.

Idempotent: running it again is a no-op. Writes capture/filename-map.csv.
"""
import csv, hashlib, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(ROOT, "site")
TEXT_EXT = {".html", ".htm", ".css", ".js"}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isdir(MIRROR):
        sys.exit(f"mirror not found: {MIRROR}")

    # 1. find every saved file whose name carries a query string
    targets = []
    for dirpath, _, filenames in os.walk(MIRROR):
        for fn in filenames:
            if "?" in fn:
                targets.append(os.path.join(dirpath, fn))

    if not targets:
        print("nothing to normalize (already clean)")
        return

    # 2. group by the base name the query strips down to
    groups = defaultdict(list)
    for full in targets:
        d, fn = os.path.split(full)
        base = fn.split("?", 1)[0]
        groups[(d, base)].append(full)

    renames, dedupes = {}, []
    for (d, base), members in sorted(groups.items()):
        stem, ext = os.path.splitext(base)
        by_hash, order = {}, []
        for full in sorted(members):
            h = sha(full)
            if h not in by_hash:
                by_hash[h] = full
                order.append(h)
        for i, h in enumerate(order):
            new = base if i == 0 else f"{stem}~{i + 1}{ext}"
            for full in sorted(members):
                if sha(full) == h:
                    renames[full] = os.path.join(d, new)
        # members sharing a hash beyond the first copy are redundant on disk
        for full in sorted(members):
            if renames[full] != full and os.path.exists(renames[full]):
                pass

    # 3. build reference-replacement table (longest first, so no partial hits)
    repl = {}
    for old, new in renames.items():
        old_fn, new_fn = os.path.basename(old), os.path.basename(new)
        for variant in (old_fn,
                        old_fn.replace("?", "%3F"),
                        old_fn.replace("?", "%3f"),
                        old_fn.replace("?", "%3F").replace("&", "&amp;"),
                        old_fn.replace("&", "&amp;")):
            repl[variant] = new_fn
    keys = sorted(repl, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys))

    # 4. rewrite references throughout the mirror
    edited = 0
    for dirpath, _, filenames in os.walk(MIRROR):
        for fn in filenames:
            if os.path.splitext(fn)[1].lower() not in TEXT_EXT:
                continue
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                text = fh.read()
            new_text = pattern.sub(lambda m: repl[m.group(0)], text)
            if new_text != text:
                with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new_text)
                edited += 1

    # 5. perform the renames (dropping byte-identical duplicates)
    rows, moved, dropped = [], 0, 0
    for old in sorted(renames):
        new = renames[old]
        rel_old = os.path.relpath(old, ROOT)
        rel_new = os.path.relpath(new, ROOT)
        if old == new:
            continue
        if os.path.exists(new):
            os.remove(old)
            dropped += 1
            rows.append({"old": rel_old, "new": rel_new, "action": "deduped"})
        else:
            os.rename(old, new)
            moved += 1
            rows.append({"old": rel_old, "new": rel_new, "action": "renamed"})

    os.makedirs(os.path.join(ROOT, "capture"), exist_ok=True)
    with open(os.path.join(ROOT, "capture", "filename-map.csv"),
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["old", "new", "action"])
        w.writeheader()
        w.writerows(rows)

    print(f"renamed {moved}, deduped {dropped}, rewrote refs in {edited} files")


if __name__ == "__main__":
    main()
