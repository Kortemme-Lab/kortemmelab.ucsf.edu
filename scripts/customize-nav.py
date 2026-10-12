#!/usr/bin/env python3
"""Remove chosen items from the site navigation, on every page.

Weebly bakes the whole menu into each of the 101 pages twice -- once in
#navigation (desktop) and once in #navmobile (the hamburger menu) -- so a nav
change is a 202-place edit, not a one-file edit. This drives that from one
list, and is idempotent, so it can simply be re-run after a fresh capture.

Each page also carries the menu a third time, as JSON handed to Weebly's
flyout-menu initializer (initPublishedFlyoutMenus), together with templates
for rendering menu items. That copy is pruned too, so the runtime can never
re-render a removed item back into the menu.

Removing a top-level item takes its dropdown with it. The underlying pages are
left on disk: they just stop being reachable, exactly like the orphans the site
already had. Delete the files separately if you want them actually gone.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

# Top-level menu entries to drop, matched on visible label or href.
HIDE = [
    {"label": "Research",  "href": "research.html"},
    {"label": "Rosetta",   "href": "rosetta.html"},
    {"label": "Our Wiki",  "href": "https://kortemmeweb.ucsf.edu/wiki"},
]

ITEM_RE = re.compile(r'<li\b[^>]*class="wsite-menu-item-wrap"[^>]*>', re.I)
LI_TOKEN = re.compile(r"<li\b|</li\s*>", re.I)
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)


def block_end(text, pos):
    """Index just past the </li> that closes the <li> opened before `pos`."""
    depth = 1
    while depth:
        m = LI_TOKEN.search(text, pos)
        if not m:
            return None
        depth += -1 if m.group(0).lower().startswith("</") else 1
        pos = m.end()
    return pos


def describe(block):
    """(label, href) of the menu item itself -- its first <a>, not its children."""
    a = ANCHOR_RE.search(block)
    if not a:
        return "", ""
    href = re.search(r'href="([^"]*)"', a.group(1))
    label = re.sub(r"<[^>]+>", " ", a.group(2))
    return re.sub(r"\s+", " ", label).strip(), (href.group(1) if href else "")


def matches(label, href):
    for want in HIDE:
        if label.casefold() == want["label"].casefold():
            return want["label"]
        if href and href == want["href"]:
            return want["label"]
    return None


def strip_nav(text):
    out, pos, removed = [], 0, []
    while True:
        m = ITEM_RE.search(text, pos)
        if not m:
            break
        end = block_end(text, m.end())
        if end is None:
            break
        label, href = describe(text[m.start():end])
        hit = matches(label, href)
        if hit:
            out.append(text[pos:m.start()])
            removed.append(hit)
        else:
            out.append(text[pos:end])
        pos = end
    out.append(text[pos:])
    return "".join(out), removed


FLYOUT_RE = re.compile(r"(initPublishedFlyoutMenus\(\s*)(\[.*?\])(\s*,)", re.S)


def weebly_dumps(obj):
    """Serialize exactly as Weebly does: compact, with escaped slashes."""
    return json.dumps(obj, separators=(",", ":")).replace("/", "\\/")


def strip_flyout_json(text):
    """Drop HIDE entries from the flyout initializer's menu JSON."""
    removed = []

    def repl(m):
        items = json.loads(m.group(2))
        keep = []
        for it in items:
            hit = matches(it.get("title", ""), it.get("url", ""))
            if hit:
                removed.append(hit)
            else:
                keep.append(it)
        return m.group(1) + weebly_dumps(keep) + m.group(3)

    return FLYOUT_RE.sub(repl, text), removed


def main():
    if not os.path.isdir(SITE):
        sys.exit(f"mirror not found: {SITE}")
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    edited, counts = 0, {}
    for fn in pages:
        p = os.path.join(SITE, fn)
        with open(p, encoding="utf-8", errors="surrogateescape") as fh:
            text = fh.read()
        new_text, removed = strip_nav(text)
        new_text, removed_json = strip_flyout_json(new_text)
        removed += [f"{r} (flyout JSON)" for r in removed_json]
        if new_text != text:
            with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(new_text)
            edited += 1
            for r in removed:
                counts[r] = counts.get(r, 0) + 1
    if not edited:
        print(f"no change -- nav already clean across {len(pages)} pages")
        return
    print(f"edited {edited}/{len(pages)} pages; menu entries removed:")
    for label, n in sorted(counts.items()):
        print(f"   {label:26s} {n:4d}")


if __name__ == "__main__":
    main()
