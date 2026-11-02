#!/usr/bin/env python3
"""Build the website: content/ in, plain HTML out in docs/.

    python3 scripts/build-site.py

Then open docs/index.html in a browser -- no server or other software needed.
GitHub Pages can publish docs/ as it is (Settings > Pages > "Deploy from a
branch", main, /docs).

What goes where:
  content/*.md                      the menu pages (Home, News, Contact, ...)
  content/current-members/*.md      one file per lab member; each gets
  content/alumni/*.md               a page in docs/people/ and a place on the
                                    Current Members or Lab Alumni roster
  content/rotation-students.csv     the "Past rotation students" list
  content/bibliography.json         the papers on Home and Publications
  theme/layout.html, theme/site.css the look of every page
  theme/carousel.js                 the Gallery's carousel (`carousel: true`)

The rosters (Current Members, Lab Alumni) are generated from the people's
files, so content/current-members.md and content/lab-alumni.md are not used.
Publication lists come from the files themselves, kept current by
scripts/render-publications.py -- run that first if you changed `publications:`
anywhere.

Old addresses (current---kosuke-seki.html and so on) get small pages that
forward to the new ones, so links elsewhere on the web keep working.

Uses only the Python standard library. Safe to re-run: docs/ is rebuilt from
scratch each time (a CNAME file there is kept).
"""
import csv, html, json, os, re, shutil, string, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib

ROOT = bib.ROOT
CONTENT = os.path.join(ROOT, "content")
SITE = os.path.join(ROOT, "site")             # the old site: images not yet moved to content/
THEME = os.path.join(ROOT, "theme")
OUT = os.path.join(ROOT, "docs")
OLD_HOST = re.compile(r"^https?://(?:www\.)?kortemmelab\.ucsf\.edu/", re.I)
ZW = "​﻿"
SITE_NAME = "Kortemme Lab @ UCSF"
DESCRIPTION = ("The Kortemme Lab at UCSF engineers biological systems, from molecules "
               "with new functions to entire organisms.")
PUBS_AUTHORS = 5                              # as on the Publications page

# The menu. A page listed here is built from content/<slug>.md, or generated
# (the two rosters). "People" has no page of its own and opens Current Members.
NAV = [
    ("Home", "index", []),
    ("People", "current-members", [("Current Members", "current-members"),
                                   ("Lab Alumni", "lab-alumni"),
                                   ("Join the Lab", "join-the-lab")]),
    ("Publications", "publications", []),
    ("News", "news", []),
    ("Gallery", "gallery", []),
    ("Contact", "contact", [("Meetings", "meetings"), ("Directions", "directions")]),
]
GENERATED = {"current-members", "lab-alumni"}

# Roster order. Anything not listed comes after, alphabetically by role.
CURRENT_ORDER = ["Principal Investigator", "Research Scientist", "Postdoctoral Scholar",
                 "Graduate Student", "Lab Technician", "Lab Manager", "Staff", "Specialist",
                 "Visiting Scholar", "Undergraduate Researcher", "High School Student"]
ALUMNI_SECTIONS = [                           # as on the old Lab Alumni page
    ("Graduate Students", ["Graduate Student"]),
    ("Postdoctoral Scholars", ["Postdoctoral Scholar", "Research Scientist"]),
    ("Visiting Scholars", ["Visiting Scholar"]),
    ("Staff", ["Staff", "Lab Manager", "Specialist", "Lab Technician"]),
    ("Undergraduate Researchers", ["Undergraduate Researcher"]),
    ("High School Students", ["High School Student"]),
]
LINK_LABELS = {"orcid": "ORCID", "scholar": "Google Scholar", "website": "Website",
               "github": "GitHub", "ucsf_profile": "UCSF Profile", "twitter": "Twitter",
               "bluesky": "Bluesky", "linkedin": "LinkedIn"}


# =============================================================================
# reading content files
# =============================================================================
def scalar(v):
    v = v.strip()
    if not v or v == "~" or v == "null":
        return ""
    if v[0] == '"':
        return bib._scalar(v)                 # a JSON-style quoted string
    if v[0] == "'":
        return v[1:-1].replace("''", "'")
    if v[0] == "[" and v[-1] == "]":          # an inline list: ["Mike Keiser", ...]
        try:
            return [str(x) for x in json.loads(v)]
        except ValueError:
            return [scalar(x) for x in v[1:-1].split(",") if x.strip()]
    if v in ("true", "false"):
        return v == "true"
    return v


def read(path):
    """A content file's header (the YAML between the --- lines) and its body.

    Understands the subset of YAML the content files use: `key: value`,
    lists of `  - item`, and one level of `  key: value` underneath a key.
    """
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n"):
        return {}, text
    head, body = text[4:].split("\n---\n", 1)
    meta, key = {}, None
    for line in head.split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^\s+-\s*(.*)$", line)
        if m and key:
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(scalar(m.group(1)))
            continue
        m = re.match(r"^\s+([\w-]+):\s*(.*)$", line)
        if m and key:
            if not isinstance(meta[key], dict):
                meta[key] = {}
            meta[key][m.group(1)] = scalar(m.group(2))
            continue
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            meta[key] = scalar(m.group(2))
    return meta, body


# =============================================================================
# Markdown
# =============================================================================
URL_IN_PARENS = r"\(((?:[^()\s]|\([^()\s]*\))+)\)"   # DOIs can contain (…)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]" + URL_IN_PARENS)
LINK_RE = re.compile(r"\[([^\]]+)\]" + URL_IN_PARENS)
BARE_URL = re.compile(r"https?://[^\s<>\"\x00]+")
ESCAPED = re.compile(r"\\([\\`*_\[\]{}()#+\-.!<>])")
ONLY_IMAGE = re.compile(r"^(?:!\[[^\]]*\]" + URL_IN_PARENS + r"|\[!\[[^\]]*\]" + URL_IN_PARENS
                        + r"\]" + URL_IN_PARENS + r")$")
CAPTION = re.compile(r"^\*([^*].*)\*$")
HEADING = re.compile(r"^(#{1,6})\s*(.*?)\s*#*$")
ITEM = re.compile(r"^(?:([-*+])|(\d+)\.)\s+(.*)$")
BLOCK_HTML = re.compile(r"^<(?:div|iframe|ol|ul|table|figure|p|section|blockquote)\b", re.I)


def inline(s, url):
    """One paragraph's Markdown text as HTML."""
    kept = []

    def keep(h):
        kept.append(h)
        return f"\x00{len(kept) - 1}\x00"

    s = ESCAPED.sub(lambda m: keep(html.escape(m.group(1))), s)
    s = IMAGE_RE.sub(lambda m: keep(f'<img src="{html.escape(url(m.group(2)))}" '
                                    f'alt="{html.escape(m.group(1))}" loading="lazy">'), s)
    # A link's text sits between \x01 and \x02 until bare URLs are found, so a
    # URL that is itself the text of a link ("Preprint at [https://…](…)")
    # isn't made into a second link inside the first.
    s = LINK_RE.sub(lambda m: keep(f'<a href="{html.escape(url(m.group(2)))}">') + "\x01"
                    + m.group(1) + "\x02" + keep("</a>"), s)

    def bare(m):
        u = m.group(0).rstrip(".,;:!?)")
        rest = m.group(0)[len(u):]
        return keep(f'<a href="{html.escape(u)}">{html.escape(u)}</a>') + rest

    s = "".join(part if part.startswith("\x01") else BARE_URL.sub(bare, part)
                for part in re.split(r"(\x01.*?\x02)", s, flags=re.S))
    s = s.replace("\x01", "").replace("\x02", "")
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    s = re.sub(r"(?<![*\w])\*(?=\S)(.+?)(?<=\S)\*(?![*\w])", r"<em>\1</em>", s, flags=re.S)
    while "\x00" in s:
        s = re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], s)
    return s.replace("\n", "<br>\n")


def figure(lines, url):
    """An image on its own line, with an optional *caption* line under it."""
    img = inline(lines[0], url)
    if not img.startswith("<a "):             # let a click open the full-size image
        src = re.search(r'src="([^"]+)"', img).group(1)
        img = f'<a href="{src}">{img}</a>'
    cap = f"\n<figcaption>{inline(CAPTION.match(lines[1]).group(1), url)}</figcaption>" \
        if len(lines) == 2 else ""
    return f"<figure>{img}{cap}</figure>"


def is_figure(lines):
    return ONLY_IMAGE.match(lines[0]) and (len(lines) == 1 or
                                           (len(lines) == 2 and CAPTION.match(lines[1])))


def markdown(text, url):
    """The Markdown the content files use, as HTML.

    Headings, paragraphs (a single line break stays a line break), - and 1.
    lists, --- rules, images and links, **bold** and *italic*. Lines of raw
    HTML pass through; <!-- comments --> are dropped. An image alone in its
    paragraph becomes a figure (with the *italic line* under it as caption),
    and a run of figures becomes a gallery grid.
    """
    lines = ["".join(c for c in ln if c not in ZW).rstrip() for ln in text.split("\n")]
    out, i = [], 0

    def starts_block(ln):
        s = ln.strip()
        return (not s or HEADING.match(s) or ITEM.match(s) or s == "---"
                or BLOCK_HTML.match(s) or s.startswith("<!--"))

    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
        elif s.startswith("<!--"):
            while "-->" not in lines[i]:
                i += 1
            i += 1
        elif BLOCK_HTML.match(s):
            j = i
            while j < len(lines) and lines[j].strip():
                j += 1
            out.append("\n".join(lines[i:j]))
            i = j
        elif s == "---":
            out.append("<hr>")
            i += 1
        elif HEADING.match(s):
            level, words = HEADING.match(s).groups()
            if words:
                out.append(f"<h{len(level)}>{inline(words, url)}</h{len(level)}>")
            i += 1
        elif ITEM.match(s):
            ordered = bool(ITEM.match(s).group(2))
            items = []
            while i < len(lines):
                s = lines[i].strip()
                m = ITEM.match(s)
                if m and bool(m.group(2)) == ordered:
                    items.append(m.group(3))
                elif s and not starts_block(s) and items:
                    items[-1] += "\n" + s         # a wrapped item
                elif not s and i + 1 < len(lines) and ITEM.match(lines[i + 1].strip()) \
                        and bool(ITEM.match(lines[i + 1].strip()).group(2)) == ordered:
                    pass                          # a blank line between items
                else:
                    break
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>\n" + "\n".join(f"<li>{inline(x, url)}</li>" for x in items)
                       + f"\n</{tag}>")
        else:
            para = []
            while i < len(lines) and not starts_block(lines[i]):
                para.append(lines[i].strip())
                i += 1
            if is_figure(para):
                out.append(figure(para, url))
            elif para == [r"\* Co-first authors"]:
                out.append('<p class="co-first-note">* Co-first authors</p>')
            else:
                out.append(f"<p>{inline(chr(10).join(para), url)}</p>")

    # group runs of two or more figures into a gallery
    grouped, run = [], []
    for block in out + [None]:
        if block and block.startswith("<figure>"):
            run.append(block)
            continue
        if len(run) > 1:
            grouped.append('<div class="gallery">\n' + "\n".join(run) + "\n</div>")
        else:
            grouped += run
        run = []
        if block is not None:
            grouped.append(block)
    return "\n".join(grouped)


# =============================================================================
# people
# =============================================================================
class Person:
    def __init__(self, path, kind):
        self.meta, self.body = read(path)
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.kind = kind                      # "current" or "alumni"
        self.name = self.meta.get("name") or self.slug.replace("-", " ").title()
        self.role = self.meta.get("role") or ""
        self.has_page = self.meta.get("profile_page") is not False

    def get(self, key):
        return self.meta.get(key) or ""

    @property
    def years(self):
        return re.sub(r"\s*-\s*", "–", self.get("years_in_lab"))

    def year_key(self):
        """Newest first: by the year they left, then the year they came."""
        ys = [int(y) for y in re.findall(r"\d{4}", self.get("years_in_lab"))]
        return (-(ys[-1] if ys else 0), -(ys[0] if ys else 0), self.name)


ENVELOPE = ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" '
            'stroke="currentColor" stroke-width="1.5"><rect x="3" y="5.5" width="18" height="13" rx="1"/>'
            '<path d="M3.5 6.5 12 13l8.5-6.5"/></svg>')


def split_education(items):
    """Education entries, and a "Postdoctoral work: …" entry kept apart from them."""
    postdoc = next((x for x in items if re.match(r"postdoctoral work:", x, re.I)), "")
    return [x for x in items if x != postdoc], re.sub(r"^postdoctoral work:\s*", "", postdoc, flags=re.I)


def plural(role):
    return role if role.endswith(("Staff", "s")) else role + "s"


def load_people():
    people = []
    for kind, folder in (("current", "current-members"), ("alumni", "alumni")):
        d = os.path.join(CONTENT, folder)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".md"):
                people.append(Person(os.path.join(d, fn), kind))
    return people


def old_roster_order(people):
    """Where each current member sat on the old Current Members page."""
    by_file = {os.path.basename(p.get("mirror_file")): p.slug for p in people if p.get("mirror_file")}
    _, body = read(os.path.join(CONTENT, "current-members.md"))
    order = []
    for f in re.findall(r"\]\((current-+[^)#]+\.html)\)", body):
        if by_file.get(f) and by_file[f] not in order:
            order.append(by_file[f])
    return {slug: n for n, slug in enumerate(order)}


# =============================================================================
# pages
# =============================================================================
class Site:
    def __init__(self):
        self.layout = string.Template(open(os.path.join(THEME, "layout.html"), encoding="utf-8").read())
        self.people = load_people()
        self.old_names = {}                   # old file name -> new path, for links
        for p in self.people:
            mf = os.path.basename(p.get("mirror_file"))
            if mf and p.has_page:
                self.old_names[mf] = f"people/{p.slug}.html"
        self.written = []

    # --- links -----------------------------------------------------------------
    def url_fixer(self, root):
        def fix(u):
            u = OLD_HOST.sub("", html.unescape(u))
            if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#|//)", u, re.I):
                return u                      # external, mailto:, or in-page
            path, _, frag = u.partition("#")
            path = self.old_names.get(path, path) or "index.html"
            return root + path + ("#" + frag if frag else "")
        return fix

    def nav(self, current, root):
        def a(label, slug, cls=""):
            active = slug == current or (cls and current in cls)
            return (f'<a href="{root}{slug}.html"' + (' class="active"' if active else "")
                    + (' aria-current="page"' if slug == current else "") + f">{label}</a>")
        out = ["<ul>"]
        for label, slug, children in NAV:
            kids = [c for _, c in children]
            if not children:
                out.append(f"  <li>{a(label, slug)}</li>")
                continue
            out.append(f"  <li>{a(label, slug, kids)}\n    <ul class=\"submenu\">")
            out += [f"      <li>{a(l, s)}</li>" for l, s in children]
            out.append("    </ul>\n  </li>")
        out.append("</ul>")
        return "\n".join("      " + ln for ln in out)

    def write(self, rel, title, content, current="", body_class="", description=DESCRIPTION):
        root = "../" * rel.count("/")
        page = self.layout.substitute(
            title=html.escape(f"{title} · {SITE_NAME}" if title else SITE_NAME),
            description=html.escape(description), root=root, body_class=body_class,
            nav=self.nav(current, root), content=content)
        path = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(page)
        self.written.append(rel)

    # --- the menu pages ------------------------------------------------------------
    def menu_page(self, slug, label):
        meta, body = read(os.path.join(CONTENT, slug + ".md"))
        if slug == "index":
            body = self.featured(meta, body)
        fix = self.url_fixer("")
        content = markdown(body, fix)
        if meta.get("carousel"):              # theme/carousel.js turns these into a carousel
            content = content.replace('<div class="gallery">', '<div class="gallery carousel">')
        if slug != "index":
            # The title goes in an <h1>; drop a first heading that only repeats it.
            m = re.match(r"\s*<h2>(.*?)</h2>\n?", content)
            if m and re.sub(r"<[^>]+>", "", m.group(1)).lower().startswith(label.lower()):
                content = content[m.end():]
            content = f"<h1>{html.escape(label)}</h1>\n{content}"
        self.write(f"{slug}.html", "" if slug == "index" else label, content, current=slug,
                   body_class="page-home" if slug == "index" else f"page-{slug}")

    def featured(self, meta, body):
        """Home: the Selected Publications and Reviews, from the bibliography."""
        E = bib.load()
        for key in ("featured_publications", "featured_reviews"):
            ids = [i for i in meta.get(key) or [] if i in E]
            items = "".join(f"<li>{bib.to_html(bib.nature(E[i], PUBS_AUTHORS))}</li>" for i in ids)
            note = ('\n<p class="co-first-note">* Co-first authors</p>'
                    if any(re.search(r"\.\*", bib.authors(E[i], PUBS_AUTHORS)) for i in ids) else "")
            body = body.replace(f"<!-- {key} -->", f"<ol>{items}</ol>{note}")
        return body

    # --- people ----------------------------------------------------------------------
    def photo(self, p, root, cls="photo"):
        if p.get("photo"):
            return f'<img class="{cls}" src="{root}{html.escape(p.get("photo"))}" alt="{html.escape(p.name)}" loading="lazy">'
        initials = "".join(w[0] for w in p.name.split()[:2] if w[0].isalpha())
        return f'<div class="no-photo" aria-hidden="true">{html.escape(initials)}</div>'

    def name_link(self, p, root):
        name = html.escape(p.name)
        return f'<a href="{root}people/{p.slug}.html">{name}</a>' if p.has_page else name

    def current_members(self):
        order = old_roster_order(self.people)
        rank = lambda p: (CURRENT_ORDER.index(p.role) if p.role in CURRENT_ORDER else len(CURRENT_ORDER),
                          p.role, order.get(p.slug, 999), p.name)
        parts, role = ["<h1>Current Members</h1>"], None
        for p in sorted((p for p in self.people if p.kind == "current"), key=rank):
            if p.role != role:                # a new section, as on the old page
                if role is not None:
                    parts.append("</ul>")
                if p.role != "Principal Investigator":
                    parts.append(f"<h2>{html.escape(plural(p.role))}</h2>")
                parts.append('<ul class="roster">')
                role = p.role
            if p.role == "Principal Investigator":
                parts.append(self.pi_card(p))
                continue
            pic = self.photo(p, "")
            if p.has_page:
                pic = f'<a href="people/{p.slug}.html" tabindex="-1">{pic}</a>'
            summary = f'\n  <p class="summary">{inline(p.get("summary"), self.url_fixer(""))}</p>' \
                if p.get("summary") else ""
            parts.append(f'<li class="member">\n  {pic}\n  <span class="name">{self.name_link(p, "")}</span>\n'
                         f'  <span class="role">{html.escape(p.role)}</span>{summary}\n</li>')
        parts.append("</ul>")
        self.write("current-members.html", "Current Members", "\n".join(parts), current="current-members",
                   body_class="page-people")

    def pi_card(self, p):
        """The PI across the full width, laid out as on the old roster page:
        summary, education and postdoctoral work beside the photo."""
        page = f"people/{p.slug}.html"
        education, postdoc = split_education(p.meta.get("education") or [])
        text = [f'<h2 class="name"><a href="{page}">{html.escape(p.name)}</a></h2>']
        if p.get("summary"):
            text.append(f'<p class="summary">{inline(p.get("summary"), self.url_fixer(""))}</p>')
        if education:
            text.append("<h3>Education</h3>\n<ul>\n" + "\n".join(f"<li>{html.escape(x)}</li>" for x in education)
                        + "\n</ul>")
        if postdoc:
            text.append(f"<h3>Postdoctoral work</h3>\n<p>{html.escape(postdoc)}</p>")
        links = [f'<a href="{page}">Bio</a>']
        if (p.meta.get("links") or {}).get("ucsf_profile"):
            links.append(f'<a href="{html.escape(p.meta["links"]["ucsf_profile"])}">UCSF Profile</a>')
        email = (f'<a class="email" href="mailto:{html.escape(p.get("email"))}" title="{html.escape(p.get("email"))}" '
                 f'aria-label="Email {html.escape(p.name)}">{ENVELOPE}</a>' if p.get("email") else "<span></span>")
        side = (f'<a href="{page}" tabindex="-1">{self.photo(p, "")}</a>\n<div class="meta">{email}'
                f'<div><strong>{html.escape(p.role)}</strong><br>{", ".join(links)}</div></div>')
        return (f'<li class="pi">\n<div class="pi-text">\n' + "\n".join(text)
                + f'\n</div>\n<div class="pi-side">\n{side}\n</div>\n</li>')

    def lab_alumni(self):
        alumni = [p for p in self.people if p.kind == "alumni" and p.role != "Rotation Student"]
        parts = ["<h1>Lab Alumni</h1>"]
        placed = set()
        sections = ALUMNI_SECTIONS + [("Other Alumni", sorted({p.role for p in alumni}
                                                              - {r for _, rs in ALUMNI_SECTIONS for r in rs}))]
        for title, roles in sections:
            group = sorted((p for p in alumni if p.role in roles), key=Person.year_key)
            if not group:
                continue
            rows = ['<li class="alumni-head"><span></span><span>Name</span><span>Years</span>'
                    '<span>After the lab</span><span>Current position</span></li>']
            for p in group:
                placed.add(p.slug)
                pic = self.photo(p, "")
                if p.has_page:
                    pic = f'<a href="people/{p.slug}.html" tabindex="-1">{pic}</a>'
                # As on the old page: one position goes under "After the lab";
                # "Current position" is filled only once they've moved on since.
                after, now = p.get("position_after_lab"), p.get("current_position")
                if not after:
                    after, now = now, ""
                rows.append(f'<li>{pic}<span class="name">{self.name_link(p, "")}</span>'
                            f'<span class="years">{html.escape(p.years)}</span>'
                            f'<span class="position">{html.escape(after)}</span>'
                            f'<span class="position">{html.escape(now)}</span></li>')
            parts.append(f"<h2>{title}</h2>\n<ul class=\"alumni\">\n" + "\n".join(rows) + "\n</ul>")
        missing = [p.name for p in alumni if p.slug not in placed]
        assert not missing, missing

        pages = {p.slug for p in self.people if p.has_page}
        rot = []
        with open(os.path.join(CONTENT, "rotation-students.csv"), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                name = html.escape(r["name"])
                if r["profile"] in pages:
                    name = f'<a href="people/{r["profile"]}.html">{name}</a>'
                rot.append(f"<li>{name}, {html.escape(r['program'])}, {html.escape(r['term'])}</li>")
        parts.append("<h2>Past Rotation Students</h2>\n<ul class=\"rotations\">\n" + "\n".join(rot) + "\n</ul>")
        self.write("lab-alumni.html", "Lab Alumni", "\n".join(parts), current="lab-alumni",
                   body_class="page-people")

    def profile(self, p):
        root = "../"
        fix = self.url_fixer(root)
        back = ("current-members", "Current Members") if p.kind == "current" else ("lab-alumni", "Lab Alumni")
        pron = f' <span class="pronouns">({html.escape(p.get("pronouns"))})</span>' if p.get("pronouns") else ""
        role = " · ".join(html.escape(x) for x in (p.role, p.get("program")) if x)
        facts = []
        if p.years:
            facts.append(f"In the lab: {html.escape(p.years)}")
        mentors = p.meta.get("co_mentors") or []
        if mentors:
            facts.append(("Co-mentors: " if len(mentors) > 1 else "Co-mentor: ")
                         + html.escape(", ".join(mentors)))
        if p.get("position_after_lab"):
            facts.append(f"After the lab: {html.escape(p.get('position_after_lab'))}")
        if p.get("current_position"):
            facts.append(f"Now: {html.escape(p.get('current_position'))}")
        links = []
        if p.get("email"):
            e = html.escape(p.get("email"))
            links.append(f'<li><a href="mailto:{e}">{e}</a></li>')
        for key, u in (p.meta.get("links") or {}).items():
            if u:
                label = LINK_LABELS.get(key, key.replace("_", " ").title())
                links.append(f'<li><a href="{html.escape(u)}">{label}</a></li>')

        head = [f"<h1>{html.escape(p.name)}{pron}</h1>"]
        if role:
            head.append(f'<p class="role">{role}</p>')
        if facts:
            head.append('<p class="facts">' + "<br>\n".join(facts) + "</p>")
        if p.get("summary"):
            head.append(f'<p class="summary">{inline(p.get("summary"), fix)}</p>')
        if links:
            head.append('<ul class="links">' + "".join(links) + "</ul>")

        # The body: anything written about them, then education, then papers.
        intro, _, pubs = p.body.partition("## Publications")
        parts = [f'<article class="profile">\n<p class="back"><a href="{root}{back[0]}.html">&larr; {back[1]}</a></p>',
                 f'<div class="profile-head">\n{self.photo(p, root)}\n<div>\n' + "\n".join(head) + "\n</div>\n</div>"]
        if intro.strip():
            parts.append(markdown(intro, fix))
        education, postdoc = split_education(p.meta.get("education") or [])
        if education:
            parts.append("<h2>Education</h2>\n<ul class=\"education\">\n"
                         + "\n".join(f"<li>{html.escape(x)}</li>" for x in education) + "\n</ul>")
        if postdoc:
            parts.append(f"<h2>Postdoctoral work</h2>\n<p>{html.escape(postdoc)}</p>")
        if "<li>" in markdown(pubs, fix):
            parts.append('<section id="publications">\n' + markdown("## Publications" + pubs, fix) + "\n</section>")
        parts.append("</article>")
        self.write(f"people/{p.slug}.html", p.name, "\n".join(parts),
                   current=back[0], body_class="page-profile",
                   description=p.get("summary") or f"{p.name}, Kortemme Lab, UCSF")

    def redirects(self):
        """The old site's addresses for profiles, forwarding to the new pages."""
        for old, new in sorted(self.old_names.items()):
            target = html.escape(new)
            with open(os.path.join(OUT, old), "w", encoding="utf-8") as fh:
                fh.write(f'<!DOCTYPE html>\n<meta charset="utf-8">\n<title>Moved</title>\n'
                         f'<link rel="canonical" href="{target}">\n'
                         f'<meta http-equiv="refresh" content="0; url={target}">\n'
                         f'<p>This page has moved to <a href="{target}">{target}</a>.</p>\n')
        return len(self.old_names)

    # --- files the pages use -------------------------------------------------------------
    def copy_assets(self):
        os.makedirs(os.path.join(OUT, "assets", "fonts"), exist_ok=True)
        for name in ("site.css", "carousel.js"):
            shutil.copyfile(os.path.join(THEME, name), os.path.join(OUT, "assets", name))
        for w in ("regular", "medium", "semibold", "bold"):
            shutil.copyfile(os.path.join(SITE, "assets", "fonts", f"raleway-{w}.woff2"),
                            os.path.join(OUT, "assets", "fonts", f"raleway-{w}.woff2"))

    def copy_images(self):
        """Every image a page refers to, from content/ or else the old site/."""
        copied, missing = set(), []
        for rel in self.written:
            page = open(os.path.join(OUT, rel), encoding="utf-8").read()
            for ref in re.findall(r'(?:src|href)="([^"]+)"', page):
                ref = html.unescape(ref)
                if re.match(r"^(?:[a-z][a-z0-9+.-]*:|#|//)", ref, re.I) or ref.endswith((".html", ".css", ".js")):
                    continue
                target = os.path.normpath(os.path.join(os.path.dirname(rel), ref.split("#")[0]))
                if target in copied or os.path.exists(os.path.join(OUT, target)):
                    continue
                src = next((os.path.join(d, target) for d in (CONTENT, SITE)
                            if os.path.isfile(os.path.join(d, target))), None)
                if not src:
                    missing.append(f"{rel}: {ref}")
                    continue
                os.makedirs(os.path.dirname(os.path.join(OUT, target)), exist_ok=True)
                shutil.copyfile(src, os.path.join(OUT, target))
                copied.add(target)
        return copied, missing

    def broken_links(self):
        broken = []
        for rel in self.written:
            page = open(os.path.join(OUT, rel), encoding="utf-8").read()
            for ref in re.findall(r'href="([^"]+)"', page):
                ref = html.unescape(ref).split("#")[0]
                if not ref or re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", ref, re.I):
                    continue
                if not os.path.exists(os.path.join(OUT, os.path.dirname(rel), ref)):
                    broken.append(f"{rel} -> {ref}")
        return broken


def clear_output():
    os.makedirs(OUT, exist_ok=True)
    for name in os.listdir(OUT):
        if name == "CNAME":
            continue
        path = os.path.join(OUT, name)
        shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
    open(os.path.join(OUT, ".nojekyll"), "w").close()   # serve files as they are


def main():
    site = Site()
    clear_output()
    site.copy_assets()
    for label, slug, children in NAV:
        for l, s in [(label, slug)] + children:
            if s not in GENERATED and not os.path.exists(os.path.join(OUT, s + ".html")):
                site.menu_page(s, l)
    site.current_members()
    site.lab_alumni()
    profiles = [p for p in site.people if p.has_page]
    for p in profiles:
        site.profile(p)
    n_redirects = site.redirects()
    copied, missing = site.copy_images()
    broken = site.broken_links()

    print(f"built docs/: {len(site.written) - len(profiles)} pages, {len(profiles)} profiles, "
          f"{n_redirects} old addresses forwarded, {len(copied)} images")
    for m in missing:
        print("   missing image:", m)
    for b in broken:
        print("   broken link:", b)
    if missing or broken:
        sys.exit(1)
    print("open docs/index.html to view it")


if __name__ == "__main__":
    main()
