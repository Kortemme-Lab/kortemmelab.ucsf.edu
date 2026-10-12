"""The lab's master bibliography: storage, DOI lookup, and Nature-style output.

content/bibliography.json is a CSL-JSON array -- the standard format read by
Zotero, Pandoc and citeproc -- with one entry per paper and each entry's `id`
set to its DOI, lowercased. Entries come from the publisher's own DOI record
(fetched once, then edited by hand if ever needed), never from parsing citation
text, so names, titles and page numbers are what the publisher registered.

Imported by build-bibliography.py and render-publications.py.
"""
import html, json, os, re, time, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB_PATH = os.path.join(ROOT, "content", "bibliography.json")
ABBR_PATH = os.path.join(ROOT, "content", "journal-abbreviations.json")
UA = "kortemmelab-site-bibliography/1.0 (+https://kortemmelab.ucsf.edu)"

# The only CSL fields kept from a DOI record. Records also carry abstracts,
# funders, licences and full reference lists, none of which a citation needs.
FIELDS = ["id", "type", "DOI", "URL", "title", "container-title",
          "container-title-short", "collection-title", "author", "issued",
          "volume", "issue", "page", "number", "publisher", "event", "note"]

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)


# =============================================================================
# DOIs and storage
# =============================================================================
def clean_doi(s):
    """Normalize a DOI found in running text or a URL."""
    s = urllib.parse.unquote(html.unescape(s)).strip()
    s = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", s, flags=re.I)
    s = re.sub(r"(?:/(?:full|abstract|pdf|epdf|meta))+$", "", s, flags=re.I)
    s = s.rstrip(".,;:'\"")
    while s.endswith(")") and s.count(")") > s.count("("):   # "(see 10.1/x)"
        s = s[:-1]
    if s.lower().startswith("10.1101/"):                      # bioRxiv's URLs add v1, v2…
        s = re.sub(r"v\d+$", "", s)
    return s.lower()


ARXIV_RE = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.I)


def find_doi(text):
    m = DOI_RE.search(text)
    if m:
        return clean_doi(m.group(0))
    m = ARXIV_RE.search(text)                                 # every arXiv ID has a DOI
    return f"10.48550/arxiv.{m.group(1)}" if m else None


def load():
    if not os.path.exists(BIB_PATH):
        return {}
    with open(BIB_PATH, encoding="utf-8") as fh:
        return {e["id"]: e for e in json.load(fh)}


def save(entries):
    """Write sorted newest first, then by first author -- stable diffs."""
    items = sorted(entries.values(), key=lambda e: (-year(e), first_family(e), e["id"]))
    with open(BIB_PATH, "w", encoding="utf-8") as fh:
        json.dump(items, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


# =============================================================================
# fetching
# =============================================================================
def _get(url, accept, tries=6):
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (404, 400, 406, 410):
                return None
            # rate-limited or busy: wait as long as the server asks
            wait = e.headers.get("Retry-After") if e.code in (429, 503) else None
            time.sleep(int(wait) + 1 if wait and wait.isdigit() else 3 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 * (attempt + 1))
    return None


def fetch(doi):
    """The publisher's record for a DOI, trimmed to citation fields."""
    rec = _get("https://doi.org/" + urllib.parse.quote(doi, safe="/:()"),
               "application/vnd.citationstyles.csl+json")
    return trim(rec) if rec else None


PREPRINT_WORDS = re.compile(r"bioRxiv|medRxiv|chemRxiv|arXiv|Research Square|preprint", re.I)


def search(citation_text):
    """Find the DOI for a citation that lacks one.

    Accepted only if the candidate's full title appears in the citation text,
    so a merely similar paper is never matched. A preprint and its published
    paper usually share a title, so a preprint is accepted only when the
    citation itself names a preprint server; peer-review reports and data
    deposits (which also reuse titles) never are.
    """
    time.sleep(1)                                             # Crossref etiquette
    url = ("https://api.crossref.org/works?rows=8&select=DOI,title,type&query.bibliographic="
           + urllib.parse.quote(citation_text[:500]))
    data = _get(url, "application/json")
    norm = lambda s: re.sub(r"[^a-z0-9]", "", html.unescape(s).lower())
    target = norm(citation_text)
    wants_preprint = bool(PREPRINT_WORDS.search(citation_text))
    for item in (data or {}).get("message", {}).get("items", []):
        title = clean_text((item.get("title") or [""])[0])   # drop <i>, <sub>, …
        kind = item.get("type", "")
        if kind in ("peer-review", "component") or (kind == "posted-content") != wants_preprint:
            continue
        if len(norm(title)) >= 20 and norm(title) in target:
            return clean_doi(item["DOI"])
    return None


def full_range(pages):
    """MEDLINE abbreviates page ranges ("E6048-57"); Nature gives them in full."""
    m = re.match(r"^([A-Za-z]*)(\d+)-([A-Za-z]*)(\d+)$", pages.strip())
    if not m:
        return pages
    pre, a, pre2, b = m.groups()
    if len(b) < len(a):
        b = a[:len(a) - len(b)] + b
    return f"{pre}{a}-{pre2 or pre}{b}"


def pubmed_pages(doi):
    """Pages from PubMed, for DOI records that omit them."""
    eutils = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    time.sleep(1.2)                                           # NCBI: max 3 requests/s
    found = _get(eutils + "esearch.fcgi?db=pubmed&retmode=json&term="
                 + urllib.parse.quote(doi + "[doi]"), "application/json") or {}
    ids = found.get("esearchresult", {}).get("idlist", [])
    if not ids:
        return None
    time.sleep(1.2)
    summary = _get(eutils + "esummary.fcgi?db=pubmed&retmode=json&id=" + ids[0], "application/json") or {}
    pages = summary.get("result", {}).get(ids[0], {}).get("pages")
    return full_range(pages) if pages else None


def published_versions(doi):
    """DOIs a preprint's own record names as its published version."""
    rec = _get("https://doi.org/" + urllib.parse.quote(doi, safe="/:()"),
               "application/vnd.citationstyles.csl+json") or {}
    return [r["id"].lower() for r in (rec.get("relation") or {}).get("is-preprint-of", [])
            if r.get("id-type", "doi") == "doi" and r.get("id")]


def trim(rec):
    out = {k: rec[k] for k in FIELDS if k in rec}
    for k in ("title", "container-title", "container-title-short", "collection-title"):
        if isinstance(out.get(k), list):
            out[k] = out[k][0] if out[k] else ""
        if isinstance(out.get(k), str):
            out[k] = clean_text(out[k])
        if not out.get(k):
            out.pop(k, None)
    # Many journals (Science, eLife, PLoS) number articles instead of giving
    # pages. Crossref records that as `article-number`, which isn't a standard
    # citation field; Zotero, Pandoc and citeproc all expect it under `page`.
    if not out.get("page") and rec.get("article-number"):
        out["page"] = str(rec["article-number"])
    # A preprint's record names its published version, if any. Kept as a
    # plain list of DOIs under `relation`, so a published paper can replace
    # its preprint wherever the preprint is listed.
    pubs = [r["id"].lower() for r in (rec.get("relation") or {}).get("is-preprint-of", [])
            if r.get("id-type", "doi") == "doi" and r.get("id")]
    if pubs:
        out["relation"] = {"is-preprint-of": pubs}
    out["DOI"] = rec.get("DOI", "")
    out["id"] = out["DOI"].lower()
    out["author"] = [{k: a[k] for k in ("family", "given", "suffix", "literal") if a.get(k)}
                     for a in rec.get("author", [])]
    if "issued" in out:
        out["issued"] = {"date-parts": out["issued"].get("date-parts", [[None]])}
    return out


def clean_text(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s))     # titles can carry <i>, <sub>, MathML
    return re.sub(r"\s+", " ", s).strip()


# =============================================================================
# finding citations on a page
# =============================================================================
YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")


def plain(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s.replace("\u200b", "").replace("\ufeff", "")).strip()


def doi_in(chunk):
    hrefs = " ".join(re.findall(r'href="([^"]+)"', chunk))
    return find_doi(plain(chunk) + " " + html.unescape(hrefs))


def looks_like_citation(chunk, strict=False):
    t = plain(chunk)
    if doi_in(chunk):
        return True
    return bool(YEAR_RE.search(t)) and len(t) > 60 and t.count(",") >= (3 if strict else 1)


def citation_spans(page_html):
    """Where a page's citations are, as (start, end, chunk) offsets.

    A page's papers are the items of its paper list(s) -- any list where most
    items look like citations. A few profiles instead list papers as
    paragraph text separated by line breaks; there, each chunk is one.
    """
    i, j = page_html.find('id="wsite-content"'), page_html.find('id="footer"')
    spans = []
    for m in re.finditer(r"<(ol|ul)\b[^>]*>(.*?)</\1>", page_html[i:j], re.S):
        items = list(re.finditer(r"<li\b[^>]*>(.*?)</li>", m.group(2), re.S))
        if items and sum(looks_like_citation(x.group(1)) for x in items) * 2 > len(items):
            base = i + m.start(2)
            spans += [(base + x.start(1), base + x.end(1), x.group(1)) for x in items]
    if spans:
        return spans, "list"
    for m in re.finditer(r'<div class="paragraph"[^>]*>(.*?)</div>', page_html[i:j], re.S):
        base, inner, pos = i + m.start(1), m.group(1), 0
        # cut at whole <br> tags only -- a pattern that could start a chunk
        # partway into "<br>" once left a stray "<" in the page
        for sep in list(re.finditer(r"<br\s*/?>", inner)) + [None]:
            end = sep.start() if sep else len(inner)
            chunk = inner[pos:end]
            if chunk.strip() and looks_like_citation(chunk, strict=True):
                spans.append((base + pos, base + end, chunk))
            pos = sep.end() if sep else len(inner)
    return spans, "paragraph"


# =============================================================================
# content-file headers
# =============================================================================
def _scalar(v):
    """A header value: a quoted string, or bare text with any # comment removed."""
    v = v.strip()
    if v.startswith('"'):
        m = re.match(r'"((?:[^"\\]|\\.)*)"', v)
        return json.loads(m.group(0)) if m else v.strip('"')
    return re.sub(r"\s+#.*$", "", v).strip()


def _head_lines(text):
    return text[4:].split("\n---\n", 1)[0].split("\n") if text.startswith("---\n") else []


def header_list(text, key):
    """A list field from a content file's header, or None if absent.

    Accepts block lists ("  - item" lines) or inline ones ("[a, b]", "[]"),
    with # comments anywhere, as a hand-edited copy of the profile template
    may have.
    """
    lines = _head_lines(text)
    for n, ln in enumerate(lines):
        m = re.match(rf"^{re.escape(key)}:[ \t]*(.*)$", ln)
        if not m:
            continue
        rest = re.sub(r"\s*#.*$", "", m.group(1)) if not m.group(1).lstrip().startswith('"') else m.group(1)
        if rest.strip().startswith("["):
            try:
                return [str(x) for x in json.loads(rest.strip())]
            except json.JSONDecodeError:
                return [_scalar(x) for x in rest.strip()[1:-1].split(",") if x.strip()]
        if rest.strip():
            return None                                   # a scalar, not a list
        vals = []
        for item in lines[n + 1:]:
            if re.match(r"^[ \t]*(#.*)?$", item):
                continue                                  # blank line or comment
            im = re.match(r"^[ \t]+- (.+)$", item)
            if not im:
                break
            vals.append(_scalar(im.group(1)))
        return vals
    return None


def header_value(text, key):
    for ln in _head_lines(text):
        m = re.match(rf"^{re.escape(key)}:[ \t]*(.+)$", ln)
        if m:
            v = _scalar(m.group(1))
            return v or None
    return None


def set_list(path, key, values):
    """Replace (or add) a YAML list field in a content file's header."""
    text = open(path, encoding="utf-8").read()
    head, sep, rest = text[4:].partition("\n---\n")
    out, skip = [], False
    for ln in head.split("\n"):
        if re.match(rf"^{key}:", ln):
            skip = True
            continue
        if skip and ln.startswith((" ", "\t")):
            continue
        skip = False
        out.append(ln)
    if values:
        out.append(f"{key}:")
        out += [f'  - "{v}"' for v in values]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\n" + "\n".join(out) + sep + rest)


# =============================================================================
# reading entries
# =============================================================================
def year(e):
    try:
        return int(e["issued"]["date-parts"][0][0])
    except (KeyError, IndexError, TypeError, ValueError):
        return 0


def date_key(e):
    try:
        parts = (e["issued"]["date-parts"][0] + [0, 0])[:3]
        return tuple(int(p or 0) for p in parts)
    except (KeyError, IndexError, TypeError, ValueError):
        return (0, 0, 0)


def first_family(e):
    a = e.get("author") or [{}]
    return (a[0].get("family") or a[0].get("literal") or "").lower()


def is_preprint(e):
    return e.get("type") in ("posted-content", "preprint", "article")


def published_version(e):
    """The DOI of a preprint's published paper, if its record names one."""
    pubs = (e.get("relation") or {}).get("is-preprint-of") or []
    return pubs[0] if pubs and is_preprint(e) else None


def has_co_first(e):
    return any(a.get("co-first") for a in e.get("author", []))


def has_author(e, family, given_initial):
    for a in e.get("author", []):
        if a.get("family", "").lower() == family.lower() and \
                (a.get("given") or given_initial)[:1].upper() == given_initial.upper():
            return True
        if family.lower() in a.get("literal", "").lower():
            return True
    return False


# =============================================================================
# Nature reference style
# =============================================================================
# Nature, as the lab wants it: every author listed on people's pages, and the
# first five then "et al." on the Publications page; "&" before the last, co-first
# authors -- `"co-first": true` on an author in bibliography.json -- marked
# with *. Names are "Family, I. I." Titles plain, the
# journal abbreviated in italics, the volume in bold, then pages or article
# number and the year in parentheses. Preprints: "Preprint at <url> (year)."
#
# Output is a list of segments so one renderer serves HTML and Markdown:
#   ("text", s)  ("i", s)  ("b", s)  ("a", s, href)

def initials(given):
    out = []
    for part in re.split(r"[\s.]+", given.strip()):
        if not part:
            continue
        if "-" in part:
            out.append("-".join(p[0].upper() + "." for p in part.split("-") if p))
        else:
            out.append(part[0].upper() + ".")
    return " ".join(out)


def person(a):
    if a.get("literal"):
        return a["literal"]
    family = a.get("family", "").strip()
    if family.isupper() and len(family) > 3:          # some old records are in capitals
        family = "-".join(w.capitalize() for w in family.lower().split("-"))
    name = f"{family}, {initials(a['given'])}" if a.get("given") else family
    return f"{name} {a['suffix']}" if a.get("suffix") else name


def authors(e, limit=None):
    """Every author, or with `limit`, that many and then "et al." """
    names = [person(a) + ("*" if a.get("co-first") else "")
             for a in e.get("author", []) if a.get("family") or a.get("literal")]
    if not names:
        return ""
    if limit and len(names) > limit:
        return ", ".join(names[:limit]) + " et al."
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " & " + names[-1]


_ABBR = None


def journal(e):
    """The journal's abbreviation, from content/journal-abbreviations.json.

    Publishers' own records abbreviate inconsistently (`Nat Commun`, `J. Mol.
    Biol.`, `Journal of Molecular Biology`), so a curated table in Nature's
    house style decides. A journal missing from the table falls back to its
    record's abbreviation; render-publications.py lists those so they can be
    added.
    """
    global _ABBR
    if _ABBR is None:
        _ABBR = {}
        if os.path.exists(ABBR_PATH):
            with open(ABBR_PATH, encoding="utf-8") as fh:
                _ABBR = {k.lower(): v for k, v in json.load(fh).items()}
    full = e.get("container-title", "")
    return _ABBR.get(full.lower()) or e.get("container-title-short") or full


def needs_abbreviation(e):
    journal(e)
    return bool(e.get("container-title")) and e["container-title"].lower() not in _ABBR \
        and not is_preprint(e) and not cited_as_book(e)


def cited_as_book(e):
    return e.get("type") in ("book-chapter", "proceedings-article", "paper-conference", "chapter") \
        and not e.get("volume")


def end_with_period(s):
    return s if s.endswith((".", "?", "!")) else s + "."


def doi_url(e):
    return "https://doi.org/" + e["DOI"] if e.get("DOI") else e.get("URL", "")


def nature(e, limit=None):
    """One reference, as segments, in Nature style (limit: see authors)."""
    seg = []
    who = authors(e, limit)
    if who:
        seg.append(("text", end_with_period(who) + " "))
    title = end_with_period(e.get("title", "").rstrip("."))
    url = doi_url(e)
    yr = year(e) or "n.d."

    if is_preprint(e):
        seg.append(("text", title + " Preprint at "))
        seg.append(("a", url, url) if url else ("text", e.get("container-title", "")))
        seg.append(("text", f" ({yr})."))
        return seg

    seg.append(("a", title[:-1], url) if url else ("text", title[:-1]))
    seg.append(("text", ". "))
    kind = e.get("type", "")
    pages = (e.get("page") or e.get("number") or "").replace("-", "–")

    if cited_as_book(e):                           # "in <book title>", unabbreviated
        seg.append(("text", "in "))
        seg.append(("i", e.get("container-title", "")))
        tail = ", ".join(x for x in (e.get("publisher", ""), str(yr)) if x)
        seg.append(("text", (f" {pages}" if pages else "") + f" ({tail})."))
    elif kind == "book":
        seg = seg[:-2] + [("i", title[:-1]), ("text", f" ({e.get('publisher', '')}, {yr}).")]
    else:
        seg.append(("i", journal(e)))
        if e.get("volume"):
            seg.append(("text", " "))
            seg.append(("b", str(e["volume"])))
            seg.append(("text", (f", {pages}" if pages else "") + f" ({yr})."))
        else:                                          # online ahead of print
            seg.append(("text", " "))
            seg.append(("a", url, url) if url else ("text", ""))
            seg.append(("text", f" ({yr})."))
    return seg


def to_html(seg):
    out = []
    for s in seg:
        t = html.escape(s[1], quote=False)
        if s[0] == "text":
            out.append(t)
        elif s[0] == "i":
            out.append(f"<em>{t}</em>")
        elif s[0] == "b":
            out.append(f"<strong>{t}</strong>")
        elif s[0] == "a":
            out.append(f'<a href="{html.escape(s[2])}" target="_blank">{t}</a>')
    return "".join(out)


def md_escape(s):
    return re.sub(r"([\\`*_\[\]<>])", r"\\\1", s)


def to_markdown(seg):
    out = []
    for s in seg:
        if s[0] == "text":
            out.append(md_escape(s[1]))
        elif s[0] == "i":
            out.append(f"*{md_escape(s[1])}*")
        elif s[0] == "b":
            out.append(f"**{md_escape(s[1])}**")
        elif s[0] == "a":
            out.append(f"[{md_escape(s[1])}]({s[2]})")
    return "".join(out)


def to_text(seg):
    return "".join(s[1] for s in seg)
