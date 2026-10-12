#!/usr/bin/env python3
"""Reorganize the mirror into a conventional static-site layout, without
changing how a single page looks.

wget leaves a site laid out the way the servers it came from were: assets
buried under the host they were fetched from
(`_cdn/cdn11.editmysite.com/images/common/checkmarks/@2x/`), photos under
Weebly's account-sharded upload path (`uploads/7/2/7/7/72776173/published/`),
and every page carrying the whole Weebly platform -- analytics, MathJax, a
login system, cookie banners. This turns that into:

    site/
      *.html               the pages, same filenames, so URLs match the live site
      images/              every content photo, flat
      images/backgrounds/  page background images
      assets/css/          Weebly base styles, the theme, fonts, slideshow
      assets/js/           jQuery, the Weebly runtime, the theme's scripts
      assets/fonts/        Raleway (woff2) and the social-icon font
      assets/img/          the few interface images actually drawn

What stays and what goes is spelled out in PLATFORM_KEEP and
DEAD_INLINE_SCRIPTS below. The rule: Weebly *platform* assets are pruned to
those some page uses in some state -- established by rendering every page at
desktop and mobile widths, hovering the menus, opening the mobile menu and
paging through the gallery -- while the site's own theme and content files are
kept whole and only reorganized.

HTML is re-indented without changing what renders. No CSS on this site uses
`white-space: pre*`, so every whitespace run collapses to a single space, and
the formatter only ever swaps one non-empty whitespace run for another: it
never adds whitespace where there was none, or removes it where there was.

Idempotent: on an already-tidy site it reports nothing to do.
"""
import argparse, csv, hashlib, os, posixpath, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOADS = "uploads/7/2/7/7/72776173/"

# --- what to keep -----------------------------------------------------------
# Platform files (fetched from Weebly's CDNs) that the site actually uses.
# Anything else under _cdn/, cdn-cgi/ or files/ is removed.
PLATFORM_KEEP = {
    "_cdn/cdn11.editmysite.com/css/sites.css":                  "assets/css/weebly.css",
    "_cdn/cdn11.editmysite.com/css/social-icons.css":           "assets/css/weebly-social-icons.css",
    "_cdn/cdn2.editmysite.com/css/old/slideshow/slideshow.css": "assets/css/weebly-slideshow.css",
    "_cdn/cdn2.editmysite.com/fonts/Raleway/font.css":          "assets/css/font-raleway.css",
    "_cdn/cdn11.editmysite.com/js/jquery-1.8.3.min.js":         "assets/js/jquery-1.8.3.min.js",
    "_cdn/cdn11.editmysite.com/js/site/main.js":                "assets/js/weebly.js",
    "_cdn/cdn2.editmysite.com/js/lang/en/stl.js":               "assets/js/weebly-strings.js",
    "_cdn/cdn2.editmysite.com/js/old/slideshow-jq.js":          "assets/js/weebly-slideshow.js",
    "_cdn/cdn2.editmysite.com/fonts/wSocial/wsocial.woff":      "assets/fonts/wsocial.woff",
    "_cdn/cdn2.editmysite.com/images/old/loading.gif":          "assets/img/weebly-loading.gif",
    "_cdn/cdn2.editmysite.com/images/old/slideshow/control_icons.gif":
                                                                "assets/img/weebly-slideshow-controls.gif",
}
# Every Raleway weight is kept -- hovering the menu pulls in `regular`, which
# no page requests at load -- but only as woff2, which every current browser
# uses. The .eot/.ttf/.woff copies existed for IE6-era browsers.
PLATFORM_KEEP_PATTERNS = [
    (re.compile(r"^_cdn/cdn2\.editmysite\.com/fonts/Raleway/([\w-]+)\.woff2$"),
     r"assets/fonts/raleway-\1.woff2"),
]
# The site's own theme: kept whole, only moved.
THEME_PATTERNS = [
    (re.compile(r"^files/main_style\.css$"),         "assets/css/theme.css"),
    (re.compile(r"^files/theme/([\w.-]+\.js)$"),     r"assets/js/theme-\1"),
    (re.compile(r"^files/theme/images/([^/]+)$"),    r"assets/img/theme-\1"),
]
PLATFORM_ROOTS = ("_cdn/", "cdn-cgi/", "files/")

# --- what to strip from every page ------------------------------------------
# Inline scripts implementing features the site does not have, or that report
# to third parties. Weebly's `_W.*` configuration assignments are deliberately
# NOT listed: the runtime may read them in states a screenshot can't exercise,
# and they are a few hundred bytes.
DEAD_INLINE_SCRIPTS = [
    (r"MathJax\.Hub",                 "MathJax config (no page contains math)"),
    (r"initCustomerAccountsModels",   "customer-accounts login system"),
    (r"_gaq\s*=",                     "Google Analytics (Universal Analytics, shut down 2023)"),
    (r"getElementsByTagName\(o\)",    "Weebly's Snowplow tracking loader"),
    (r"forceShowCcLinks",             "cookie-consent link shim"),
    (r"div\.blog-social div\.fb-like", "Facebook-like shim for blog posts"),
    (r"fullCalendar",                 "calendar init with a placeholder ID; its plugin is never loaded"),
]

WS = " \t\n\r\f"                      # HTML whitespace -- NOT  , which renders
WS_RUN = re.compile(r"[ \t\n\r\f]+")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
RAW = {"script", "style", "title", "textarea"}
CLOSES_P = {"address", "article", "aside", "blockquote", "details", "div", "dl",
            "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2",
            "h3", "h4", "h5", "h6", "header", "hgroup", "hr", "main", "menu",
            "nav", "ol", "p", "pre", "section", "table", "ul"}
INDENT = "  "


# =============================================================================
# planning
# =============================================================================
def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def plan(site):
    """Map every non-page file to its new home, or to None (removed)."""
    moves, content = {}, {}
    for dirpath, _, filenames in os.walk(site):
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), site).replace(os.sep, "/")
            if fn == ".DS_Store":
                moves[rel] = None
            elif "/" not in rel and rel.endswith(".html"):
                continue                                  # pages stay put
            elif rel.startswith("uploads/"):
                sub = rel[len(UPLOADS):] if rel.startswith(UPLOADS) else rel[len("uploads/"):]
                if sub.startswith("background-images/"):
                    content[rel] = "images/backgrounds/" + posixpath.basename(sub)
                else:
                    content[rel] = "images/" + posixpath.basename(sub)
            elif rel.startswith(PLATFORM_ROOTS):
                new = PLATFORM_KEEP.get(rel)
                for pat, repl in PLATFORM_KEEP_PATTERNS + THEME_PATTERNS:
                    if new is None and pat.match(rel):
                        new = pat.sub(repl, rel)
                moves[rel] = new

    # Flattening Weebly's published/ and editor/ folders can land two files on
    # one name. Byte-identical copies collapse into one file; genuinely
    # different images get a -2, -3 suffix.
    by_target = {}
    for old, new in sorted(content.items()):
        by_target.setdefault(new, []).append(old)
    for target, olds in by_target.items():
        hashes = {}
        for old in olds:
            h = sha(os.path.join(site, old))
            if h not in hashes:
                n = len(hashes) + 1
                stem, ext = posixpath.splitext(target)
                hashes[h] = target if n == 1 else f"{stem}-{n}{ext}"
            moves[old] = hashes[h]
    return moves


# =============================================================================
# CSS
# =============================================================================
URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""")


def resolve(ref, from_dir):
    """Turn a reference into a site-relative path (or None if external)."""
    if re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", ref, re.I):
        return None
    path = ref.split("#")[0].split("?")[0]
    if not path:
        return None
    base = "" if path.startswith("/") else from_dir
    return posixpath.normpath(posixpath.join(base, path.lstrip("/")))


def relref(target, from_dir):
    return posixpath.relpath(target, from_dir or ".")


def drop_empty_rules(css):
    """Remove `selector {}` rules (and @-blocks left empty). Declares nothing."""
    while True:
        new = re.sub(r"[^{}]*\{\s*\}", "", css)
        if new == css:
            return css
        css = new


def split_top(s, sep=","):
    parts, depth, cur = [], 0, ""
    for c in s:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        if c == sep and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += c
    parts.append(cur)
    return parts


def rewrite_css(css, old_dir, new_dir, moves, dangling):
    def target_of(ref):
        t = resolve(ref, old_dir)
        return t, (moves.get(t, t) if t is not None else None)

    # @font-face: keep only sources that survive; drop blocks left with none
    def fix_font_face(block):
        block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
        decls = []
        for decl in split_top(block[block.index("{") + 1:block.rindex("}")], ";"):
            if not decl.strip():
                continue
            prop, _, val = decl.partition(":")
            if prop.strip().lower() != "src":
                decls.append(f"{prop.strip()}: {val.strip()}")
                continue
            keep = []
            for entry in split_top(val):
                u = URL_RE.search(entry)
                if u:
                    old_t, new_t = target_of(u.group(2))
                    if old_t is not None and new_t is None:
                        continue                              # source removed
                    if old_t is not None:
                        entry = entry.replace(u.group(0), f"url('{relref(new_t, new_dir)}')")
                keep.append(entry.strip())
            if keep:
                decls.append("src: " + ", ".join(keep))
        if not any(d.startswith("src:") for d in decls):
            return ""                                         # no font left
        head = block[:block.index("{")].strip()
        return head + " {\n  " + ";\n  ".join(decls) + ";\n}"

    def fix_url(m):
        old_t, new_t = target_of(m.group(2))
        if old_t is None:
            return m.group(0)
        if new_t is None:
            # only background(-image) declarations reach here on this site,
            # where `none` draws exactly what a missing image draws: nothing
            return "none"
        if not os.path.exists(os.path.join(SITE, old_t)) and old_t == new_t:
            dangling.append(old_t)
        return f"url('{relref(new_t, new_dir)}')"

    # Each url() is rewritten exactly once: @font-face blocks by their own
    # pass (which can drop sources), everything else by the generic one.
    parts = re.split(r"(@font-face\s*\{[^}]*\})", css)
    for i, part in enumerate(parts):
        parts[i] = fix_font_face(part) if i % 2 else URL_RE.sub(fix_url, part)
    return drop_empty_rules("".join(parts))


# =============================================================================
# HTML: strip dead weight, repoint references
# =============================================================================
TAG_RE = re.compile(r"<script\b[^>]*>.*?</script>|<link\b[^>]*>", re.S | re.I)
REF_RE = re.compile(r"""(?<![\w/.-])/?((?:uploads|_cdn|files|cdn-cgi)/[^"'\s)<>\\]+)""")
SLIDE_URL_RE = re.compile(r'("url"\s*:\s*")((?:\d+\\?/){5}[^"]+)(")')


def attr(tag, name):
    m = re.search(r"""\b%s\s*=\s*(["'])(.*?)\1""" % name, tag, re.S | re.I)
    return m.group(2) if m else None


def strip_dead(html, moves, report):
    seen = set()

    def judge(m):
        tag = m.group(0)
        name = "script" if tag[:7].lower() == "<script" else "link"
        url = attr(tag, "src") if name == "script" else attr(tag, "href")
        if name == "link" and (attr(tag, "rel") or "").lower() != "stylesheet":
            return tag
        if url:
            t = resolve(url, "")
            if t is not None and t in moves and moves[t] is None:
                report["removed external file refs"] += 1
                return ""
            if t is not None:
                if t in seen:
                    report["removed duplicate includes"] += 1
                    return ""
                seen.add(t)
            return tag
        if name == "script":
            body = tag[tag.index(">") + 1:]
            for pat, _why in DEAD_INLINE_SCRIPTS:
                if re.search(pat, body):
                    report["removed dead inline scripts"] += 1
                    return ""
        return tag

    html = TAG_RE.sub(judge, html)
    html, n = re.subn(r'<div id="customer-accounts-app">\s*</div>', "", html)
    html, n2 = re.subn(r'<meta property="og:image"[^>]*og-image-placeholder-blank[^>]*>', "", html)
    return html


SAME_SITE_URL_RE = re.compile(
    r"""url\(\s*(['"]?)https?://kortemmelab\.ucsf\.edu/([^'")]+)\1\s*\)""")


def upstream_404s():
    """Site paths the capture saw return 404, read from the wget log."""
    for log in (os.path.join(ROOT, "capture", "wget-mirror.log"),
                os.path.join(ROOT, "wget-mirror.log")):
        if os.path.exists(log):
            missing, url = set(), None
            for line in open(log, encoding="utf-8", errors="replace"):
                if line.startswith("--"):
                    url = line.split()[-1]
                elif "ERROR 404" in line and url:
                    m = re.match(r"https?://kortemmelab\.ucsf\.edu/(.+)", url)
                    if m:
                        missing.add(m.group(1).split("?")[0])
            return missing
    return set()


def repoint(html, moves, dangling):
    def fix(m):
        t = posixpath.normpath(m.group(1).split("#")[0].split("?")[0])
        if t in moves:
            if moves[t] is None:
                dangling.append(t)
                return m.group(0)
            return moves[t]
        return m.group(0)

    html = REF_RE.sub(fix, html)

    # Inline styles sometimes name this site's own files by absolute URL,
    # which wget leaves pointing at the live server. Use the local copy; if
    # the capture saw the file 404 upstream, `none` draws exactly what a 404
    # draws. Anything else is left alone -- never silently drop an image that
    # was live but simply not captured.
    def fix_abs(m):
        path = m.group(2).split("?")[0]
        if moves.get(path):
            return f"url('{moves[path]}')"
        if path in UPSTREAM_404:
            REPORT["dead live-site background URLs -> none"] += 1
            return "none"
        REPORT["absolute live-site URLs left as-is"] += 1
        return m.group(0)

    html = SAME_SITE_URL_RE.sub(fix_abs, html)

    # Slideshow payloads name photos relative to /uploads/; the patched
    # slideshow script now prefixes images/ instead, so give it the new name.
    def fix_slide(m):
        escaped = "\\/" in m.group(2)
        old = "uploads/" + m.group(2).replace("\\/", "/")
        new = moves.get(old)
        if not new or not new.startswith("images/"):
            dangling.append(old)
            return m.group(0)
        name = new[len("images/"):]
        return m.group(1) + (name.replace("/", "\\/") if escaped else name) + m.group(3)

    return SLIDE_URL_RE.sub(fix_slide, html)


# =============================================================================
# HTML: re-indent
# =============================================================================
ATTR_RE = re.compile(r"""([^\s"'>/=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?""")


def scan_tag_end(s, i):
    n, j = len(s), i + 1
    while j < n:
        c = s[j]
        if c == ">":
            return j
        if c == "=":
            j += 1
            while j < n and s[j] in WS:
                j += 1
            if j < n and s[j] in "\"'":
                k = s.find(s[j], j + 1)
                j = n - 1 if k < 0 else k
        j += 1
    return n - 1


def tokenize(s):
    toks, i, n = [], 0, len(s)
    end_re = re.compile(r"</([A-Za-z][A-Za-z0-9:-]*)[^>]*>")
    name_re = re.compile(r"[A-Za-z][A-Za-z0-9:-]*")
    while i < n:
        if s.startswith("<!--", i):
            j = s.find("-->", i + 4)
            j = n if j < 0 else j + 3
            toks.append(["comment", s[i:j]]); i = j
        elif s.startswith("<!", i) or s.startswith("<?", i):
            j = s.find(">", i)
            j = n if j < 0 else j + 1
            toks.append(["decl", s[i:j]]); i = j
        elif s.startswith("</", i) and end_re.match(s, i):
            m = end_re.match(s, i)
            toks.append(["end", m.group(0), m.group(1).lower()]); i = m.end()
        elif s[i] == "<" and i + 1 < n and s[i + 1].isalpha():
            j = scan_tag_end(s, i)
            name = name_re.match(s, i + 1).group(0).lower()
            toks.append(["start", s[i:j + 1], name]); i = j + 1
            if name in RAW:
                close = re.compile(r"</%s\s*>" % name, re.I).search(s, i)
                k = close.start() if close else n
                toks.append(["raw", s[i:k]])
                if close:
                    toks.append(["end", close.group(0), name])
                i = close.end() if close else n
        else:
            j = s.find("<", i + 1)
            j = n if j < 0 else j
            if toks and toks[-1][0] == "text":
                toks[-1][1] += s[i:j]
            else:
                toks.append(["text", s[i:j]])
            i = j
    return toks


def clean_tag(tag, name):
    """Collapse attribute whitespace; prefer double quotes. Values verbatim."""
    inner = tag[1 + len(name):-1]
    selfclose = inner.rstrip().endswith("/")
    if selfclose:
        inner = inner.rstrip()[:-1]
    parts = []
    for m in ATTR_RE.finditer(inner):
        key, dq, sq, uq = m.groups()
        if key.lower() == "type" and name in ("script", "style", "link") and \
                (dq or sq or uq or "").lower() in ("text/javascript", "text/css"):
            continue                                   # the HTML5 default
        if dq is not None:
            parts.append(f'{key}="{dq}"')
        elif sq is not None:
            parts.append(f'{key}="{sq}"' if '"' not in sq else f"{key}='{sq}'")
        elif uq is not None:
            parts.append(f'{key}="{uq}"')
        else:
            parts.append(key)
    original_name = tag[1:1 + len(name)]
    slash = " /" if selfclose and name not in VOID else ""
    return "<" + original_name + "".join(" " + p for p in parts) + slash + ">"


def reindent_raw(body, name, lvl):
    """Indent an inline script/style body one level inside its tag.

    Only each line's leading whitespace changes, which JS and CSS ignore --
    except inside template literals and backslash-continued strings, so any
    block containing either is left exactly as it was.
    """
    if name not in ("script", "style") or not body.strip():
        return body
    if "`" in body or re.search(r"\\\n", body):
        return body
    parts = []
    for line in body.replace("\r\n", "\n").split("\n"):
        n = len(line) - len(line.lstrip(" \t"))
        lead, rest = line[:n].expandtabs(4), line[n:].rstrip()
        if rest:
            parts.append((lead, rest))
    common = min(len(lead) for lead, _ in parts)
    lines = ["\n" + INDENT * lvl + lead[common:] + rest for lead, rest in parts]
    return "".join(lines) + "\n" + INDENT * (lvl - 1)


def reindent(html):
    toks = [t for t in tokenize(html.replace("\r\n", "\n")) if t[0] != "comment"]
    merged = []                                      # rejoin text split by comments
    for t in toks:
        if t[0] == "text" and merged and merged[-1][0] == "text":
            merged[-1][1] += t[1]
        else:
            merged.append(t)
    toks = merged

    stack = []
    def level(st):
        return sum(1 for x in st if x != "html")

    def close_implied(name):
        if name == "body" and "head" in stack:
            del stack[stack.index("head"):]
        if stack and stack[-1] == "p" and name in CLOSES_P:
            stack.pop()
        pairs = {"li": ("li", {"ul", "ol"}), "dt": ("dt", {"dl"}), "dd": ("dd", {"dl"}),
                 "td": ("td", {"tr"}), "th": ("th", {"tr"}),
                 "tr": ("tr", {"table", "tbody", "thead", "tfoot"}),
                 "option": ("option", {"select", "datalist"})}
        if name in pairs:
            own, containers = pairs[name]
            peers = {own} | ({"td", "th"} if own in ("td", "th") else set()) | \
                    ({"dt", "dd"} if own in ("dt", "dd") else set())
            for k in range(len(stack) - 1, -1, -1):
                if stack[k] in containers:
                    break
                if stack[k] in peers:
                    del stack[k:]
                    break

    def level_after_end(name):
        if name in stack:
            k = len(stack) - 1 - stack[::-1].index(name)
            return level(stack[:k])
        return level(stack)

    out = []
    for idx, t in enumerate(toks):
        kind = t[0]
        if kind == "text":
            nxt = toks[idx + 1] if idx + 1 < len(toks) else None
            pieces = re.findall(r"[ \t\n\r\f]+|[^ \t\n\r\f]+", t[1])
            for p_i, p in enumerate(pieces):
                if p[0] not in WS:
                    out.append(p)
                elif "\n" in p:
                    trailing = p_i == len(pieces) - 1
                    lvl = level_after_end(nxt[2]) if trailing and nxt and nxt[0] == "end" else level(stack)
                    out.append("\n" + INDENT * lvl)
                else:
                    out.append(" ")
        elif kind == "decl":
            out.append("<!DOCTYPE html>" if t[1].lower().startswith("<!doctype html") else t[1])
        elif kind == "start":
            name = t[2]
            close_implied(name)
            in_head = "head" in stack and "body" not in stack
            if in_head and out and not out[-1].startswith("\n") and name != "head":
                out.append("\n" + INDENT * level(stack))   # one head element per line
            out.append(clean_tag(t[1], name))
            if name not in VOID:
                stack.append(name)
        elif kind == "raw":
            prev = toks[idx - 1] if idx else None
            name = prev[2] if prev and prev[0] == "start" else ""
            out.append(reindent_raw(t[1], name, level(stack)))
        elif kind == "end":
            name = t[2]
            if name in stack:
                k = len(stack) - 1 - stack[::-1].index(name)
                del stack[k:]
            out.append(f"</{name}>")
    text = "".join(out).strip("\n") + "\n"
    return re.sub(r"[ \t]+\n", "\n", text)


def tidy_head(html):
    """Modern charset declaration first in <head>; drop empty CSS rules."""
    html = re.sub(r'<meta http-equiv="Content-Type" content="text/html; charset=utf-8"\s*/?>',
                  "", html, flags=re.I)
    if '<meta charset="utf-8">' not in html:
        html = re.sub(r"(<head\b[^>]*>)", r'\1\n<meta charset="utf-8">', html, count=1, flags=re.I)

    def fix_style(m):
        return m.group(1) + drop_empty_rules(m.group(2)) + m.group(3)

    return re.sub(r"(<style\b[^>]*>)(.*?)(</style>)", fix_style, html, flags=re.S | re.I)


# =============================================================================
# main
# =============================================================================
def main():
    global SITE
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--site", default=os.path.join(ROOT, "site"))
    ap.add_argument("--map", default=os.path.join(ROOT, "capture", "asset-map.csv"),
                    help="where to record old -> new paths")
    args = ap.parse_args()
    SITE = os.path.abspath(args.site)

    if not os.path.isdir(os.path.join(SITE, "_cdn")) and \
            not os.path.isdir(os.path.join(SITE, "uploads")):
        print("already tidy -- nothing to do")
        return

    global UPSTREAM_404, REPORT
    UPSTREAM_404 = upstream_404s()
    moves = plan(SITE)
    report = REPORT = {"removed external file refs": 0, "removed duplicate includes": 0,
                       "removed dead inline scripts": 0,
                       "dead live-site background URLs -> none": 0,
                       "absolute live-site URLs left as-is": 0}
    dangling = []

    # 1. pages: strip, repoint, tidy head, re-indent -- in memory
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    new_pages, before, after = {}, 0, 0
    for fn in pages:
        html = open(os.path.join(SITE, fn), encoding="utf-8", errors="surrogateescape").read()
        before += len(html.encode("utf-8", "surrogateescape"))
        html = strip_dead(html, moves, report)
        html = repoint(html, moves, dangling)
        html = reindent(tidy_head(html))
        after += len(html.encode("utf-8", "surrogateescape"))
        new_pages[fn] = html

    # 2. stylesheets and scripts that survive: rewritten in memory
    texts = {}
    for old, new in moves.items():
        if new and old.endswith(".css"):
            css = open(os.path.join(SITE, old), encoding="utf-8", errors="surrogateescape").read()
            texts[new] = rewrite_css(css, posixpath.dirname(old), posixpath.dirname(new),
                                     moves, dangling)
        elif new == "assets/js/weebly-slideshow.js":
            js = open(os.path.join(SITE, old), encoding="utf-8", errors="surrogateescape").read()
            # Weebly resolves slideshow photos against a root-relative
            # /uploads/; point it at images/ -- relative, so the gallery now
            # also works when a page is opened straight from disk.
            texts[new] = js.replace('"/uploads/"+', '"images/"+')

    # The slideshow derives each full-size photo's name by appending _orig,
    # so every renamed photo must still have its _orig partner beside it.
    targets = {v for v in moves.values() if v}
    for fn, html in new_pages.items():
        for m in re.finditer(r'"url"\s*:\s*"([^"/\\]+\.(?:jpe?g|png|gif))"', html):
            stem, ext = posixpath.splitext(m.group(1))
            for need in (f"images/{m.group(1)}", f"images/{stem}_orig{ext}"):
                if need not in targets:
                    dangling.append(f"{fn}: slideshow needs {need}")

    if dangling:
        print(f"ABORTED, nothing written: {len(set(dangling))} references would break:")
        for d in sorted(set(dangling))[:25]:
            print("   ", d)
        sys.exit(1)

    for fn, html in new_pages.items():
        with open(os.path.join(SITE, fn), "w", encoding="utf-8", errors="surrogateescape") as fh:
            fh.write(html)

    # 3. move and delete
    rows = []
    for old in sorted(moves):
        new = moves[old]
        src = os.path.join(SITE, old)
        if new is None:
            os.remove(src)
            rows.append({"old": old, "new": "", "action": "removed"})
            continue
        dest = os.path.join(SITE, new)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if new in texts:
            with open(dest, "w", encoding="utf-8", errors="surrogateescape") as fh:
                fh.write(texts[new])
            if os.path.abspath(src) != os.path.abspath(dest):
                os.remove(src)
            rows.append({"old": old, "new": new, "action": "moved+rewritten"})
        elif os.path.exists(dest) and os.path.abspath(src) != os.path.abspath(dest):
            os.remove(src)                       # byte-identical duplicate
            rows.append({"old": old, "new": new, "action": "deduplicated"})
        else:
            shutil.move(src, dest)
            rows.append({"old": old, "new": new, "action": "moved"})

    for dirpath, dirnames, filenames in sorted(os.walk(SITE), key=lambda x: -len(x[0])):
        if dirpath != SITE and not os.listdir(dirpath):
            os.rmdir(dirpath)

    os.makedirs(os.path.dirname(args.map), exist_ok=True)
    with open(args.map, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["old", "new", "action"])
        w.writeheader()
        w.writerows(rows)

    acts = {}
    for r in rows:
        acts[r["action"]] = acts.get(r["action"], 0) + 1
    print(f"pages: {len(pages)}  HTML {before/1e6:.2f} MB -> {after/1e6:.2f} MB")
    for k, v in report.items():
        print(f"  {k}: {v}")
    for k, v in sorted(acts.items()):
        print(f"  files {k}: {v}")


if __name__ == "__main__":
    main()
