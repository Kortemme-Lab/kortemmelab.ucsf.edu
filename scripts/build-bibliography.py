#!/usr/bin/env python3
"""Create content/bibliography.json from the papers listed across the site.

Run once. It reads every citation on the Publications page and on each
person's profile in archive/site/, finds each paper's DOI -- in the citation's text or
links, or failing that by a Crossref title search that only accepts a
candidate whose full title appears in the citation -- and stores the
publisher's record for it. Each person's content file gets a `publications:`
list of the DOIs their profile listed.

From then on the bibliography and those lists are the source of truth, and
render-publications.py draws every list from them. So this refuses to
overwrite an existing bibliography; pass --force to rebuild from scratch,
discarding any hand edits to it.

Writes archive/capture/citation-migration.csv: every original citation, where it was,
and which entry it became.
"""
import argparse, concurrent.futures as cf, csv, html, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib
from extract import ROOT, content_index, content_path

SITE = os.path.join(ROOT, "archive", "site")
PEOPLE_RE = re.compile(r"^(?:current|alumni)-{2,}.+\.html$")
plain, doi_in = bib.plain, bib.doi_in

# DOIs checked by hand for citations the automatic search rightly won't
# guess at: the citation's wording differs slightly from the published title.
# Matched by a phrase from the citation.
MANUAL_DOIS = [
    # site: "...to Assay Protein Methyltransferase PRMT5"; published: "...to Assay
    # the Protein..." -- same authors, Assay Drug Dev. Technol., 2015
    ("Radioactive Filter Binding to Assay", "10.1089/adt.2015.640"),
]

# Chapters in numbered book series, whose DOI records omit the series volume.
# Nature cites these like journals (Methods Enzymol. 523, 61-85), so the volume
# is needed. Each was checked against both the lab's citation and PubMed.
SERIES_VOLUMES = {
    "10.1007/978-1-4939-3569-7_12": "1414",         # Methods Mol. Biol.
    "10.1007/978-1-4939-7893-9_12": "1798",         # Methods Mol. Biol.
    "10.1016/b978-0-12-394292-0.00004-7": "523",    # Methods Enzymol.
    "10.1016/b978-0-12-394292-0.00006-0": "523",    # Methods Enzymol.
    "10.1016/b978-0-12-381270-4.00019-6": "487",    # Methods Enzymol.
    "10.1016/s0065-3233(05)72001-5": "72",          # Adv. Protein Chem.
}
SERIES_NOTE = "Series volume added by hand (the DOI record omits it); checked against PubMed."

# DOI records whose author list is incomplete, corrected from PubMed (which
# gives initials only -- and initials are all Nature style shows).
AUTHOR_FIXES = {
    "10.1093/nar/gkh785": [  # record lists only Chen; PubMed and the lab: five authors
        {"family": "Chen", "given": "Y"}, {"family": "Kortemme", "given": "T"},
        {"family": "Robertson", "given": "T"}, {"family": "Baker", "given": "D"},
        {"family": "Varani", "given": "G"}],
}
AUTHOR_NOTE = "Author list completed by hand from PubMed; the DOI record lists only the first author."

# Papers with no DOI record anywhere this script can reach. Each is matched by
# a phrase from its citation and entered from what the lab's own citation
# states -- no name or detail beyond that is filled in.
MANUAL_ENTRIES = [
    ("SAT-based protein design", {
        "id": "ollikainen-2009-sat-based-protein-design",
        "type": "paper-conference",
        "title": "SAT-based protein design",
        "container-title": "Proc. 2009 IEEE/ACM International Conference on Computer-Aided Design",
        "page": "128-135",
        "publisher": "IEEE",
        "issued": {"date-parts": [[2009]]},
        "URL": "https://ieeexplore.ieee.org/document/5361301",
        "author": [{"family": "Ollikainen", "given": "N"}, {"family": "Sentovich", "given": "E"},
                   {"family": "Coelho", "given": "C"}, {"family": "Kuehlmann", "given": "A"},
                   {"family": "Kortemme", "given": "T"}],
        "note": "Hand-made entry: no DOI record could be found for this ICCAD 2009 paper. "
                "Details are as the lab's own citation gives them.",
    }),
]


def set_list(path, key, values):
    """Replace (or add) a YAML list field in a content file's frontmatter."""
    text = open(path, encoding="utf-8").read()
    head, sep, rest = text[4:].partition("\n---\n")
    lines, out, skip = head.split("\n"), [], False
    for ln in lines:
        if re.match(rf"^{key}:", ln):
            skip = True
            continue
        if skip and ln.startswith("  "):
            continue
        skip = False
        out.append(ln)
    if values:
        out.append(f"{key}:")
        out += [f'  - "{v}"' for v in values]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("---\n" + "\n".join(out) + sep + rest)


def main():
    ap = argparse.ArgumentParser(description="Create content/bibliography.json from the site's citations.")
    ap.add_argument("--force", action="store_true", help="rebuild even if the bibliography exists")
    ap.add_argument("--site", default=SITE,
                    help="where to read the original pages (default: archive/site/, as first captured)")
    args = ap.parse_args()
    site = os.path.abspath(args.site)
    if os.path.exists(bib.BIB_PATH) and not args.force:
        print("content/bibliography.json already exists -- nothing to do (--force rebuilds it)")
        return

    pages = ["publications.html"] + sorted(f for f in os.listdir(site) if PEOPLE_RE.match(f))
    drawn = [f for f in pages if "publications:start" in open(os.path.join(site, f), encoding="utf-8").read()]
    if drawn:
        # Those lists were drawn from the bibliography: harvesting them would
        # record generated text as each page's "original" citations.
        sys.exit(f"STOPPED -- {len(drawn)} pages in {site} already show lists drawn by "
                 "render-publications.py.\nRebuild from the original pages instead: a fresh "
                 "capture, or --site pointing at an untouched copy.")
    harvested = []                                  # (page, position, chunk)
    for fn in pages:
        raw = open(os.path.join(site, fn), encoding="utf-8").read()
        for n, (_, _, chunk) in enumerate(bib.citation_spans(raw)[0], 1):
            harvested.append((fn, n, chunk))
    print(f"harvested {len(harvested)} citations from {len(pages)} pages")

    # 1. every DOI written into a citation, fetched once each
    dois = sorted({d for _, _, c in harvested if (d := doi_in(c))})
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        records = dict(zip(dois, ex.map(bib.fetch, dois)))
    print(f"DOIs in the citations: {len(dois)}, resolved {sum(1 for r in records.values() if r)}")

    # 2. citations with no DOI, or one that doesn't resolve: verified search
    resolved, rows, entries = {}, [], {}
    for fn, n, chunk in harvested:
        d, method = doi_in(chunk), "doi"
        rec = records.get(d) if d else None
        for phrase, known in MANUAL_DOIS:
            if rec is None and phrase.lower() in plain(chunk).lower():
                rec = records.get(known) or bib.fetch(known)
                records[known], method = rec, "DOI checked by hand"
        if rec is None:
            found = bib.search(plain(chunk))
            if found:
                rec = records.get(found) or bib.fetch(found)
                records[found] = rec
                method = "title search" if not d else "title search (DOI in text didn't resolve)"
        if rec is None:
            for phrase, entry in MANUAL_ENTRIES:
                if phrase.lower() in plain(chunk).lower():
                    rec, method = entry, "hand-made entry (no DOI record exists)"
        if rec is None:
            method = "UNRESOLVED"
        else:
            entries[rec["id"]] = rec
        resolved[(fn, n)] = rec["id"] if rec else None
        rows.append({"page": fn, "position": n, "id": rec["id"] if rec else "",
                     "method": method, "doi_in_text": d or "", "original_citation": plain(chunk)})

    # Some DOI records carry no pages (several PNAS papers, for one); PubMed does
    for i, e in entries.items():
        if e.get("volume") and not e.get("page") and not bib.is_preprint(e) and i.startswith("10."):
            found = bib.pubmed_pages(i)           # (not "pages": that's the page list)
            if found:
                e["page"] = found
                e["note"] = (e.get("note", "") + " Pages added from PubMed; the DOI record omits them.").strip()

    for doi, people_ in AUTHOR_FIXES.items():
        if doi in entries:
            entries[doi]["author"], entries[doi]["note"] = people_, AUTHOR_NOTE

    # A preprint whose own record names a published version that is also on
    # the site is the same work listed twice: keep only the published paper.
    # Preprints published elsewhere are reported, not swapped -- that would
    # change what someone's page lists.
    superseded, elsewhere = {}, []
    for i in [i for i, e in entries.items() if bib.is_preprint(e)]:
        for pub in bib.published_versions(i):
            if pub in entries:
                superseded[i] = pub
            else:
                elsewhere.append((i, pub))
    for pre in superseded:
        del entries[pre]
    for r in rows:
        r["listed_as"] = superseded.get(r["id"], r["id"])

    # 3. each person's list, in their page's order, without repeats
    index = content_index()
    people = 0
    for fn in pages[1:]:
        ids = list(dict.fromkeys(superseded.get(resolved[(f, n)], resolved[(f, n)])
                                 for f, n, _ in harvested if f == fn and resolved[(f, n)]))
        path = os.path.join(ROOT, content_path(fn[:-5], index))
        if ids and os.path.exists(path):
            set_list(path, "publications", ids)
            people += 1

    for doi, vol in SERIES_VOLUMES.items():
        if doi in entries and not entries[doi].get("volume"):
            entries[doi]["volume"], entries[doi]["note"] = vol, SERIES_NOTE

    bib.save(entries)
    os.makedirs(os.path.join(ROOT, "archive", "capture"), exist_ok=True)
    with open(os.path.join(ROOT, "archive", "capture", "citation-migration.csv"), "w", newline="",
              encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    methods = {}
    for r in rows:
        methods[r["method"]] = methods.get(r["method"], 0) + 1
    print(f"bibliography: {len(entries)} papers   people with a list: {people}")
    for k, v in sorted(methods.items(), key=lambda kv: -kv[1]):
        print(f"   {v:4d} citations matched by {k}")
    for pre, pub in superseded.items():
        print(f"   preprint {pre} listed as its published version {pub}")
    if elsewhere:
        print("   preprints published since, whose published version isn't on the site:")
        for pre, pub in elsewhere:
            print(f"      {pre} -> {pub}")
    for r in rows:
        if r["method"] == "UNRESOLVED":
            print(f"   unresolved: {r['page']} #{r['position']}: {r['original_citation'][:110]}")


if __name__ == "__main__":
    main()
