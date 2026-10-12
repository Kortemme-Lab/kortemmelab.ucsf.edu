#!/usr/bin/env python3
"""Extract clean content + site structure from the wget mirror of kortemmelab.ucsf.edu.

Reads:  site/*.html                        (the site's web root)
Writes: content/<slug>.md                  (one markdown file per page, w/ frontmatter)
        content/current-members/<name>.md  (people pages, filed by status --
        content/alumni/<name>.md            see content_path)
        structure/site-structure.json      (nav tree + per-page metadata)
        structure/pages.csv                (flat index)
        structure/images.csv               (every image used, w/ local path)

content/ is meant to be edited -- and its files moved -- by hand, so a
page's existing file is never overwritten or relocated; pass --refresh to
regenerate files from site/. structure/ is always rebuilt.

Stdlib only (html.parser) -- no third-party dependencies.
"""
import argparse, csv, html, json, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIRROR = os.path.join(ROOT, "site")
CONTENT = os.path.join(ROOT, "content")
STRUCT = os.path.join(ROOT, "structure")
SITE = "https://kortemmelab.ucsf.edu"

SKIP_TAGS = {"script", "style", "noscript"}
BLOCK = {"p", "div", "br", "li", "tr", "table", "blockquote", "section", "hr",
         "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "td"}
# HTML void elements never carry a closing tag, so they must not move the
# nesting depth -- otherwise region capture never sees its own </div>.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


CF_EMAIL_RE = re.compile(
    r"(?:https?://[^\"'#]*)?/cdn-cgi/l/email-protection#([0-9a-fA-F]+)")


def decode_cf_email(hexstr):
    """Undo Cloudflare's XOR email obfuscation (first byte is the key)."""
    try:
        data = bytes.fromhex(hexstr)
        key = data[0]
        return "".join(chr(b ^ key) for b in data[1:])
    except (ValueError, IndexError):
        return ""


def deobfuscate_emails(raw):
    """Rewrite Cloudflare-protected links back to plain mailto: URLs."""
    def repl(m):
        addr = decode_cf_email(m.group(1))
        return f"mailto:{addr}" if "@" in addr else m.group(0)
    return CF_EMAIL_RE.sub(repl, raw)


SLIDESHOW_RE = re.compile(r"images:\s*(\[\{.*?\}\])", re.S)


def slideshow_images(raw):
    """Pull images out of Weebly's JS slideshow payloads.

    Gallery photos are rendered by `wSlideshow.render({... images:[...] ...})`
    rather than <img> tags, so they are invisible to both a crawler and an
    HTML-only parser. Their captions are real page content.
    """
    out = []
    for m in SLIDESHOW_RE.finditer(raw):
        try:
            items = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        for im in items:
            url = im.get("url")
            if url:
                # a bare name means tidy-site.py has moved it to images/
                src = ("/uploads/" if "/" in url else "images/") + url
                out.append({"src": src,
                            "caption": html.unescape(im.get("caption", ""))})
    return out


class Region(HTMLParser):
    """Capture the raw inner HTML of the element bearing a given id.

    Nesting is tracked by counting only the target element's OWN tag name.
    Counting every tag does not work on real-world HTML: elements with
    optional end tags (<p>, <li>, <td>) are routinely left unclosed, so a
    count-everything depth drifts upward and never returns to zero -- the
    capture then runs to the end of the document and swallows the footer
    and mobile nav. Same-name counting only needs <div> to be balanced.
    """

    def __init__(self, target_id):
        super().__init__(convert_charrefs=False)
        self.target_id = target_id
        self.target_tag = None
        self.depth = None
        self.buf = []

    def handle_starttag(self, tag, attrs):
        if self.depth is None:
            if dict(attrs).get("id") == self.target_id:
                self.target_tag = tag
                self.depth = 0
            return
        if self.depth < 0:
            return
        if tag == self.target_tag and tag not in VOID:
            self.depth += 1
        self.buf.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.depth is not None and self.depth >= 0:
            self.buf.append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if self.depth is None or self.depth < 0:
            return
        if tag == self.target_tag:
            if self.depth == 0:
                self.depth = -1  # the target element just closed
                return
            self.depth -= 1
        self.buf.append(f"</{tag}>")

    def handle_data(self, d):
        if self.depth is not None and self.depth >= 0:
            self.buf.append(d)

    def handle_entityref(self, n):
        self.handle_data(f"&{n};")

    def handle_charref(self, n):
        self.handle_data(f"&#{n};")

    def handle_comment(self, data):
        if self.depth is not None and self.depth >= 0:
            self.buf.append(f"<!--{data}-->")

    @property
    def html(self):
        return "".join(self.buf) if self.depth is not None else ""


BLANK = " \t\n\r\f\v\u200b\ufeff"         # whitespace, plus zero-width characters


class ToMarkdown(HTMLParser):
    """Very small HTML -> Markdown converter for Weebly content blocks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.heading = None
        self.link = None
        self.link_text = []
        self.list_stack = []
        self.li_index = []
        self.bold = 0
        self.span_bold = []           # one flag per open <span>: did it open bold?
        self.italic = 0
        self.marks = []               # open ** / * markers: (marker, buffer, index)
        self.images = []
        self.links = []

    # --- helpers -------------------------------------------------------
    def emit(self, s):
        (self.link_text if self.link else self.out).append(s)

    def nl(self, n=1):
        if self.link:
            return
        while self.out and self.out[-1] == "\n" and n > 0:
            n -= 1
            self.out.pop()
        self.out.append("\n" * max(n, 0) if n else "")
        self.out.append("\n")

    # --- tags ----------------------------------------------------------
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP_TAGS:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.nl(1)
            self.heading = int(tag[1])
            self.out.append("#" * self.heading + " ")
        elif tag == "p" or tag == "div":
            self.nl(1)
        elif tag == "br":
            self.out.append("  \n")
        elif tag in ("strong", "b"):
            self.bold += 1
            self.open_mark("**")
        elif tag == "span":
            # Weebly sometimes bolds with a styled span instead of <strong> --
            # notably the 2005-2017 year headings on the Publications page
            bold = bool(re.search(r"font-weight\s*:\s*(?:bold|[6-9]00)", a.get("style") or "", re.I))
            self.span_bold.append(bold)
            if bold:
                self.bold += 1
                self.open_mark("**")
        elif tag in ("em", "i"):
            self.italic += 1
            self.open_mark("*")
        elif tag in ("ul", "ol"):
            self.nl(1)
            self.list_stack.append(tag)
            self.li_index.append(0)
        elif tag == "li":
            indent = "  " * (len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ol":
                self.li_index[-1] += 1
                marker = f"{self.li_index[-1]}. "
            else:
                marker = "- "
            self.out.append("\n" + indent + marker)
        elif tag == "a":
            href = a.get("href", "")
            self.link = href
            self.link_text = []
            if href:
                self.links.append(href)
        elif tag == "img":
            src = a.get("src", "")
            alt = (a.get("alt") or "").strip()
            if src:
                self.images.append(src)
                self.emit(f"\n![{alt}]({src})\n")
        elif tag == "hr":
            self.nl(1)
            self.out.append("---\n")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in ("img", "br", "hr"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = None
            self.nl(1)
        elif tag in ("p", "div"):
            self.nl(1)
        elif tag in ("strong", "b"):
            if self.bold:
                self.bold -= 1
                self.close_mark("**")
        elif tag == "span":
            if self.span_bold and self.span_bold.pop() and self.bold:
                self.bold -= 1
                self.close_mark("**")
        elif tag in ("em", "i"):
            if self.italic:
                self.italic -= 1
                self.close_mark("*")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
                self.li_index.pop()
            self.nl(1)
        elif tag == "a":
            href, text = self.link, "".join(self.link_text).strip()
            self.link = None
            self.link_text = []
            if text and href:
                self.out.append(f"[{text}]({href})")
            elif text:
                self.out.append(text)

    def open_mark(self, m):
        buf = self.link_text if self.link else self.out
        self.marks.append((m, buf, len(buf)))
        buf.append(m)

    def close_mark(self, m):
        """Close ** or *, tidily: Weebly often bolds nothing but line breaks
        or zero-width spaces, which would leave a lone `**` in the Markdown.
        An empty span gets no markers; edge whitespace moves outside them."""
        for k in range(len(self.marks) - 1, -1, -1):
            if self.marks[k][0] == m:
                _, buf, idx = self.marks.pop(k)
                break
        else:
            return
        current = self.link_text if self.link else self.out
        if buf is not current or idx >= len(buf) or buf[idx] != m:
            current.append(m)                     # crossed a link boundary
            return
        inner = "".join(buf[idx + 1:])
        core = inner.strip(BLANK)                 # zero-width spaces count as blank
        if not core:
            buf[idx:] = [inner]                   # nothing visible: no markers
            return
        lead = inner[:len(inner) - len(inner.lstrip(BLANK))]
        trail = inner[len(inner.rstrip(BLANK)):]
        buf[idx:] = [lead, m, core, m, trail]

    def handle_comment(self, data):
        word = data.strip().split()[0] if data.strip() else ""
        if word in ("publications:start", "publications:end"):
            self.nl(1)
            self.out.append(f"<!-- {word} -->\n")

    def handle_data(self, d):
        if self.skip:
            return
        if not d.strip():
            if self.out and not self.out[-1].endswith((" ", "\n")):
                self.emit(" ")
            return
        self.emit(re.sub(r"[ \t\r\f\v]+", " ", d.replace(" ", " ")))

    @property
    def markdown(self):
        text = "".join(self.out)
        text = text.replace("****", "")              # adjacent bold spans: merge
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"\n +", "\n", text)
        return text.strip() + "\n"


def page_title(raw):
    m = re.search(r"<title>(.*?)</title>", raw, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def nav_tree(raw):
    """Parse the #navigation region into a list of {title, href, children}."""
    region = Region("navigation")
    region.feed(raw)
    nav = region.html
    items, stack = [], []

    class NavP(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.cur = None
            self.text = []
            self.depth_ul = 0

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "ul":
                self.depth_ul += 1
            elif tag == "a":
                self.cur = {"title": "", "href": a.get("href", ""),
                            "level": self.depth_ul, "children": []}
                self.text = []

        def handle_data(self, d):
            if self.cur is not None and d.strip():
                self.text.append(d.strip())

        def handle_endtag(self, tag):
            if tag == "ul":
                self.depth_ul = max(0, self.depth_ul - 1)
            elif tag == "a" and self.cur is not None:
                self.cur["title"] = " ".join(self.text).strip()
                if self.cur["title"]:
                    items.append(self.cur)
                self.cur = None

    p = NavP()
    p.feed(nav)
    # nest by level, de-duplicating repeated mobile-nav copies
    tree, seen = [], set()
    for it in items:
        key = (it["title"], it["href"])
        if key in seen:
            continue
        seen.add(key)
        node = {"title": it["title"], "href": it["href"], "children": []}
        if it["level"] <= 1 or not tree:
            tree.append(node)
        else:
            tree[-1]["children"].append(node)
    return tree


def reachable_from_home(mirror, files):
    """Which pages can actually be reached by following links from index.html.

    A page can sit in the sitemap and still be unreachable by a visitor --
    Weebly keeps publishing pages that have been unlinked from the navigation.
    Those orphans matter for a rebuild: some are stale duplicates to drop,
    others are real content that was accidentally cut adrift.
    """
    pages = set(files)
    seen, queue = {"index.html"}, ["index.html"]
    while queue:
        cur = queue.pop()
        raw = open(os.path.join(mirror, cur), encoding="utf-8",
                   errors="replace").read()
        for nxt in re.findall(r'href="([a-z0-9\-]+\.html)"', raw):
            if nxt in pages and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


# Header fields this script writes. Anything else in a content file's header --
# years_in_lab, publications, or a field added by hand -- survives --refresh.
GENERATED_FIELDS = {"title", "slug", "source_url", "mirror_file", "word_count",
                    "reachable_from_home", "images", "external_links"}


def preserved_fields(path):
    """Raw header lines of the fields extract.py doesn't own."""
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n"):
        return []
    keep, mine = [], False
    for ln in text[4:].split("\n---\n", 1)[0].split("\n"):
        m = re.match(r"^([A-Za-z0-9_-]+):", ln)
        if m:
            mine = m.group(1) not in GENERATED_FIELDS
        if mine:
            keep.append(ln)
    return keep


PEOPLE_RE = re.compile(r"^(current|alumni)-{2,}(.+)$")
PEOPLE_DIRS = {"current": "current-members", "alumni": "alumni"}


def content_index():
    """Every Markdown file already in content/, by filename."""
    index = {}
    for dirpath, _, filenames in os.walk(CONTENT):
        for fn in filenames:
            if fn.endswith(".md"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
                index.setdefault(fn, []).append(rel)
    return index


def content_path(slug, index):
    """Where a page's Markdown lives, relative to the project root.

    Wherever a page's file already sits in content/ wins, so files can be
    filed by hand: graduating someone is moving their file from
    current-members/ to alumni/, and retiring a page is moving it to archive/.
    The defaults below only decide where a file goes the first time it is
    created. People are filed by status, named without the live site's
    `current---`/`alumni---` slug prefix; everything else goes at the top.
    """
    m = PEOPLE_RE.match(slug)
    name = (m.group(2) if m else slug) + ".md"
    found = sorted(index.get(name, []))
    if len(found) > 1:
        print(f"warning: {name} exists in {len(found)} places ({', '.join(found)});"
              f" using {found[0]} -- delete the stale copies", file=sys.stderr)
    if found:
        return found[0]
    return f"content/{PEOPLE_DIRS[m.group(1)]}/{name}" if m else f"content/{name}"


def main():
    ap = argparse.ArgumentParser(description="Regenerate structure/ and fill in content/.")
    ap.add_argument("--refresh", nargs="*", metavar="SLUG",
                    help="overwrite existing content/ files from site/, discarding "
                         "hand edits: all of them, or only the pages named "
                         "(by site slug, e.g. lab-alumni current---yulia-gutierrez)")
    refresh = ap.parse_args().refresh          # None, [] (= all) or [slugs]
    index = content_index()
    written = kept = 0
    os.makedirs(CONTENT, exist_ok=True)
    os.makedirs(STRUCT, exist_ok=True)
    if not os.path.isdir(MIRROR):
        sys.exit(f"mirror not found: {MIRROR}")

    files = sorted(f for f in os.listdir(MIRROR) if f.endswith(".html"))
    if refresh:
        unknown = sorted(set(refresh) - {f[:-5] for f in files})
        if unknown:
            sys.exit(f"--refresh: no such page in site/: {', '.join(unknown)}")
    reachable = reachable_from_home(MIRROR, files)
    pages, all_images, nav = [], [], None

    for fn in files:
        path = os.path.join(MIRROR, fn)
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = deobfuscate_emails(fh.read())

        slug = fn[:-5]
        title = page_title(raw)
        if nav is None:
            nav = nav_tree(raw)

        region = Region("wsite-content")
        region.feed(raw)
        body = region.html
        conv = ToMarkdown()
        conv.feed(body)
        md = conv.markdown

        shots = slideshow_images(raw)
        if shots:
            lines = ["", f"## Gallery ({len(shots)} images)", ""]
            for sh in shots:
                cap = sh["caption"].strip()
                lines.append(f"![{cap}]({sh['src'].lstrip('/')})")
                if cap:
                    lines.append(f"*{cap}*")
                lines.append("")
            md = (md.rstrip() + "\n" + "\n".join(lines)).strip() + "\n"
            conv.images.extend(sh["src"] for sh in shots)

        imgs = []
        for src in dict.fromkeys(conv.images):
            # every page sits at the mirror root, so both the relative srcs
            # wget rewrote and the absolute ones in slideshow payloads
            # resolve under site/
            local = "site/" + src.lstrip("/")
            imgs.append(local)
            all_images.append({"page": slug, "src": src, "local_path": local})

        ext_links = [l for l in dict.fromkeys(conv.links)
                     if l.startswith("http") and "kortemmelab.ucsf.edu" not in l]

        fm = ["---", f"title: {json.dumps(title)}", f"slug: {slug}",
              f"source_url: {SITE}/{fn}",
              f"mirror_file: site/{fn}",
              f"word_count: {len(md.split())}",
              f"reachable_from_home: {str(fn in reachable).lower()}"]
        if imgs:
            fm.append("images:")
            fm += [f"  - {i}" for i in imgs]
        if ext_links:
            fm.append("external_links:")
            fm += [f"  - {l}" for l in ext_links]
        fm.append("---\n")

        rel = content_path(slug, index)
        dest = os.path.join(ROOT, rel)
        redo = refresh is not None and (not refresh or slug in refresh)
        if redo or not os.path.exists(dest):
            fm[2:2] = preserved_fields(dest)          # right after the title
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as out:
                out.write("\n".join(fm) + "\n" + md)
            written += 1
        else:
            kept += 1

        pages.append({"slug": slug, "title": title,
                      "source_url": f"{SITE}/{fn}",
                      "mirror_file": f"site/{fn}",
                      "content_file": rel,
                      "word_count": len(md.split()),
                      "reachable_from_home": fn in reachable,
                      "image_count": len(imgs),
                      "external_link_count": len(ext_links)})

    with open(os.path.join(STRUCT, "site-structure.json"), "w", encoding="utf-8") as fh:
        json.dump({"site": SITE, "platform": "Weebly",
                   "page_count": len(pages), "navigation": nav or [],
                   "pages": pages}, fh, indent=2)

    with open(os.path.join(STRUCT, "pages.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(pages[0].keys()))
        w.writeheader()
        w.writerows(pages)

    with open(os.path.join(STRUCT, "images.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["page", "src", "local_path"])
        w.writeheader()
        w.writerows(all_images)

    orphans = [p for p in pages if not p["reachable_from_home"]]
    print(f"pages: {len(pages)}  images: {len(all_images)}  "
          f"nav top-level: {len(nav or [])}  "
          f"unreachable from home: {len(orphans)}")
    print(f"content/: {written} written, {kept} existing left as-is"
          + ("" if refresh is not None else " (use --refresh to regenerate)"))


if __name__ == "__main__":
    main()
