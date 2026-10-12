#!/usr/bin/env python3
"""Draw every publication list on the site from content/bibliography.json.

- A person's list is the papers named in the `publications:` field of their
  content file, newest first. Tanja Kortemme's is kept complete: any paper in
  the bibliography with her as an author is added to it.
- The Publications page is every paper in the bibliography with Tanja
  Kortemme as an author: preprints first, then by year. It names the first
  five authors, then "et al."; people's pages name every author.
- A preprint is never shown once its published version is known (its DOI
  record names it): the published paper replaces it in every person's list,
  and on the Publications page. Pass --check-preprints to ask doi.org again
  whether any listed preprint has since been published.

Everything is in Nature reference style, and is written both into the page in
site/ and into its Markdown in content/, between `publications:start` and
`publications:end` markers -- so a list is redrawn without touching anything
else on the page.

To add a paper, add its DOI to the `publications:` list of each lab member who
wrote it and run this; DOIs not yet in the bibliography are looked up
automatically. Papers with Tanja as an author appear on the Publications page
by themselves.

Also writes structure/papers.csv. Idempotent.
"""
import argparse, csv, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib
from extract import ROOT

SITE = os.path.join(ROOT, "site")
CONTENT = os.path.join(ROOT, "content")
PI = ("Kortemme", "T")
PI_PAGE = "site/current---tanja-kortemme.html"
CO_FIRST_NOTE = "* Co-first authors"
PUBS_AUTHORS = 5          # the Publications page lists this many, then "et al."
MARKERS = re.compile(r"<!--\s*publications:start.*?<!--\s*publications:end\s*-->", re.S)
HTML_START = ("<!-- publications:start (generated from content/bibliography.json "
              "by scripts/render-publications.py) -->")
HTML_END = "<!-- publications:end -->"
MD_NOTE = ("<!-- Generated from content/bibliography.json by scripts/render-publications.py. "
           "To change this list, edit `publications:` in this file's header. -->")
PUBS_NOTE = ("<!-- Generated from content/bibliography.json by scripts/render-publications.py: "
             "every paper with Tanja Kortemme as an author. -->")


# --- what to draw -----------------------------------------------------------
def people():
    """Content files that carry a publications list: (path, ids, site page)."""
    found = []
    for dirpath, _, files in os.walk(CONTENT):
        for fn in sorted(files):
            if not fn.endswith(".md") or fn == "publications.md":
                continue
            path = os.path.join(dirpath, fn)
            text = open(path, encoding="utf-8").read()
            ids = bib.header_list(text, "publications")
            if ids is not None:
                found.append((path, [i.lower() for i in ids], bib.header_value(text, "mirror_file")))
    return found


def newest_first(ids, E):
    return sorted(ids, key=lambda i: (tuple(-x for x in bib.date_key(E[i])), bib.first_family(E[i]), i))


def sections_for_pi(E, superseded):
    pubs = [i for i, e in E.items() if bib.has_author(e, *PI) and i not in superseded]
    pre = newest_first([i for i in pubs if bib.is_preprint(E[i])], E)
    rest = [i for i in pubs if not bib.is_preprint(E[i])]
    out = [("Pre-prints", pre)] if pre else []
    for y in sorted({bib.year(E[i]) for i in rest}, reverse=True):
        out.append((f"{y} Publications", newest_first([i for i in rest if bib.year(E[i]) == y], E)))
    return pubs, out


# --- drawing ----------------------------------------------------------------
def html_list(ids, E, limit=None):
    return "<ol>" + "".join(f"<li>{bib.to_html(bib.nature(E[i], limit))}</li>" for i in ids) + "</ol>"


def md_list(ids, E, limit=None):
    return "\n".join(f"{n}. {bib.to_markdown(bib.nature(E[i], limit))}" for n, i in enumerate(ids, 1))


def with_note(ids, E, html, md, limit=None):
    """Add the co-first legend under a list where a * actually shows."""
    if any(re.search(r"\.\*", bib.authors(E[i], limit)) for i in ids):
        return html + f"<br>{CO_FIRST_NOTE}", md + "\n\n" + bib.md_escape(CO_FIRST_NOTE)
    return html, md


# --- writing ------------------------------------------------------------------
def write_if_changed(path, new):
    old = open(path, encoding="utf-8").read()
    if new == old:
        return "unchanged"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return "updated"


def put_html(path, inner, whole_publications_page=False):
    """Put a generated block where the page's papers are."""
    raw = open(path, encoding="utf-8").read()
    block = HTML_START + inner + HTML_END
    if MARKERS.search(raw):
        return write_if_changed(path, MARKERS.sub(lambda m: block, raw, count=1))

    spans, kind = bib.citation_spans(raw)        # first time: find the old list
    if not spans:
        # No papers on the page yet. Some profiles still have Weebly's empty
        # "Publications" heading: the list goes under it, as on the others.
        i, j = raw.find('id="wsite-content"'), raw.find('id="footer"')
        for m in re.finditer(r'<div class="paragraph"[^>]*>(.*?)</div>', raw[i:j], re.S):
            if re.sub(r"<[^>]+>|&#8203;|\u200b|\s", "", m.group(1)) == "Publications":
                at = i + m.end(1)
                return write_if_changed(path, raw[:at] + "<br><br>" + block + raw[at:])
        return "no list found"
    start, end = spans[0][0], spans[-1][1]
    if kind == "list":
        start = max(raw.rfind("<ol", 0, start), raw.rfind("<ul", 0, start))
        close = re.compile(r"\s*</li>\s*</(?:ol|ul)>").match(raw, end)
        end = close.end() if close else end
        if whole_publications_page:
            # take in the "Pre-prints" heading that introduces the first list
            h = re.search(r"<strong>[^<]*</strong>\s*$", raw[:start])
            if h:
                start = h.start()
    else:
        # don't cut through a heading whose closing tags trail into the first
        # citation, as on Yulia Gutierrez's profile
        lead = re.match(r"(?:\s*</[^>]+>)+", raw[start:end])
        if lead:
            start += lead.end()
    return write_if_changed(path, raw[:start] + block + raw[end:])


def put_md(path, body, note):
    text = open(path, encoding="utf-8").read()
    block = f"<!-- publications:start -->\n{note}\n\n{body}\n\n<!-- publications:end -->"
    if MARKERS.search(text):
        return write_if_changed(path, MARKERS.sub(lambda m: block, text, count=1))
    content = text.split("\n---\n", 1)[1] if text.startswith("---\n") else text
    if any(bib.looks_like_citation(ln) for ln in content.split("\n")):
        return "needs markers"                    # an old list is still there
    return write_if_changed(path, text.rstrip("\n") + "\n\n## Publications\n\n" + block + "\n")


# --- main -----------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Draw every publication list from the bibliography.")
    ap.add_argument("--check-preprints", action="store_true",
                    help="ask doi.org whether any preprint has since been published")
    args = ap.parse_args()
    E = bib.load()
    if not E:
        sys.exit("content/bibliography.json is missing -- run build-bibliography.py first")
    folks = people()

    if args.check_preprints:
        for i, e in E.items():
            if bib.is_preprint(e):
                pubs = bib.published_versions(i)
                if pubs:
                    e["relation"] = {"is-preprint-of": pubs}
                else:
                    e.pop("relation", None)
        bib.save(E)

    # papers named in someone's list but not yet in the bibliography
    missing = sorted({i for _, ids, _ in folks for i in ids if i not in E})
    added, failed = 0, []
    for i in missing:
        rec = bib.fetch(i) if i.startswith("10.") else None
        if not rec:
            failed.append(i)
        elif rec["id"] != i:                       # the DOI redirects to another
            failed.append(f"{i} (its record is {rec['id']}; use that instead)")
        else:
            E[i] = rec
            added += 1
    if failed:
        sys.exit("STOPPED -- not found in the bibliography or at doi.org:\n  " + "\n  ".join(failed))
    # preprints that have been published: fetch the paper, then show it instead
    superseded, swapped = {}, []
    for i, e in list(E.items()):
        pub = bib.published_version(e)
        if pub and pub not in E:
            rec = bib.fetch(pub)
            if rec and rec["id"] == pub:
                E[pub] = rec
                added += 1
        if pub and pub in E:
            superseded[i] = pub
    if added:
        bib.save(E)

    tab = {i for i, e in E.items() if bib.has_author(e, *PI) and i not in superseded}
    for n, (path, ids, page) in enumerate(folks):
        new = list(dict.fromkeys(superseded.get(i, i) for i in ids))
        if page == PI_PAGE:
            new += sorted(tab - set(new))                     # Tanja's list: complete
        if new != ids:
            swapped += [(os.path.relpath(path, CONTENT)[:-3], i, superseded[i]) for i in ids if i in superseded]
            if page == PI_PAGE and tab - set(ids):
                print(f"Tanja Kortemme's list: added {len(tab - set(ids))} papers")
            bib.set_list(path, "publications", new)
            folks[n] = (path, new, page)

    counts = {}
    def tally(kind, result):
        counts.setdefault(kind, {}).setdefault(result, 0)
        counts[kind][result] += 1

    needs_markers, listed_on = [], {}
    for path, ids, page in folks:
        if not ids and not MARKERS.search(open(path, encoding="utf-8").read()):
            continue                             # no papers yet: no empty section
        ids = newest_first(list(dict.fromkeys(ids)), E)
        rel = os.path.relpath(path, CONTENT)[:-3]
        for i in ids:
            listed_on.setdefault(i, []).append(rel)
        html, md = with_note(ids, E, html_list(ids, E), md_list(ids, E))
        if page and os.path.exists(os.path.join(ROOT, page)):
            tally("site pages", put_html(os.path.join(ROOT, page), html))
        r = put_md(path, md, MD_NOTE)
        tally("Markdown files", r)
        if r == "needs markers":
            needs_markers.append(os.path.basename(page or "")[:-5])

    pubs, sections = sections_for_pi(E, superseded)
    all_ids = [i for _, ids in sections for i in ids]
    L = PUBS_AUTHORS
    html, md = with_note(all_ids, E,
                         "<br>".join(f"<strong>{h}</strong>{html_list(ids, E, L)}" for h, ids in sections),
                         "\n\n".join(f"### {h}\n\n{md_list(ids, E, L)}" for h, ids in sections), L)
    tally("site pages", put_html(os.path.join(SITE, "publications.html"), html, whole_publications_page=True))
    r = put_md(os.path.join(CONTENT, "publications.md"), md, PUBS_NOTE)
    tally("Markdown files", r)
    if r == "needs markers":
        needs_markers.append("publications")

    os.makedirs(os.path.join(ROOT, "structure"), exist_ok=True)
    with open(os.path.join(ROOT, "structure", "papers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "year", "type", "tanja_kortemme_author", "listed_on", "citation"])
        for i in newest_first(list(E), E):
            w.writerow([i, bib.year(E[i]) or "", E[i].get("type", ""),
                        "yes" if i in pubs else "no", "; ".join(listed_on.get(i, [])),
                        bib.to_text(bib.nature(E[i]))])

    print(f"bibliography: {len(E)} papers ({added} newly looked up)")
    for who, pre, pub in swapped:
        print(f"  {who}: preprint {pre} -> published {pub}")
    print(f"people lists: {len(folks)}   Publications page: {len(pubs)} papers in {len(sections)} sections")
    for kind, res in counts.items():
        print(f"  {kind}: " + ", ".join(f"{v} {k}" for k, v in sorted(res.items())))
    unabbreviated = sorted({E[i]["container-title"] for i in E if bib.needs_abbreviation(E[i])})
    if unabbreviated:
        print("\nJournals not in content/journal-abbreviations.json (add Nature-style abbreviations):")
        for j in unabbreviated:
            print("  ", j)
    if needs_markers:
        print("\nThese Markdown files still hold their old list. Run once, then run this again:")
        print("  python3 scripts/extract.py --refresh " + " ".join(sorted(needs_markers)))


if __name__ == "__main__":
    main()
