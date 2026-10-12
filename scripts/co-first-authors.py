#!/usr/bin/env python3
"""Mark co-first authors in the bibliography, from the lab's own citations.

DOI records don't say who contributed equally, but the lab's original
citations did, with an asterisk: "Glasgow A*, Glasgow J*, Limonta D...". This
reads those citations (capture/citation-migration.csv), works out which author
each asterisk belongs to, and sets `"co-first": true` on that author in
content/bibliography.json. The renderer then marks them with *.

An asterisk belongs to the author whose surname comes just before it, with
only initials or nothing in between -- and when two authors share a surname
(A. Glasgow and J. Glasgow), the initials decide. Asterisks in notes such as
"*co-first author" are skipped, and any asterisk that can't be placed is
reported rather than guessed.

Hand edits win: a paper that already has co-first authors marked is left
alone. Idempotent.
"""
import csv, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib

MIGRATION = os.path.join(bib.ROOT, "capture", "citation-migration.csv")
# between a surname and its asterisk: initials only, if anything, with any
# punctuation -- "Glasgow A*", "Kapp, GT*", "Filipiak, DJ,*", "Ó Conchúir*, S"
GAP_RE = re.compile(r"^[\s,.]*((?:[A-Z]\.?\s*){0,4})[\s,.]*$")


def starred(citation, entry):
    """Indices of the authors an original citation marks with *."""
    hits, missed = set(), 0
    for m in re.finditer(r"\*", citation):
        after = citation[m.end():m.end() + 12].lower().lstrip()
        if after.startswith(("co-first", "equal", "these")):
            continue                                     # a legend, not a mark
        window = citation[max(0, m.start() - 60):m.start()]
        best = None
        for n, a in enumerate(entry.get("author", [])):
            fam = a.get("family", "")
            if len(fam) < 2:
                continue
            k = window.lower().rfind(fam.lower())
            if k < 0:
                continue
            gap = GAP_RE.match(window[k + len(fam):])
            if not gap:
                continue
            initials = re.sub(r"[^A-Z]", "", gap.group(1))
            if initials and (a.get("given") or "?")[0].upper() != initials[0]:
                continue                                 # same surname, other person
            end = k + len(fam)
            if best is None or end > best[0]:
                best = (end, n)
        if best:
            hits.add(best[1])
        else:
            missed += 1
    return hits, missed


def main():
    entries = bib.load()
    found, unplaced = {}, []
    for r in csv.DictReader(open(MIGRATION, encoding="utf-8")):
        text, i = r["original_citation"], r.get("listed_as") or r["id"]
        if "*" not in text or i not in entries:
            continue
        hits, missed = starred(text, entries[i])
        found.setdefault(i, set()).update(hits)
        if missed:
            unplaced.append((r["page"], i))

    marked = kept = 0
    for i, idx in found.items():
        e = entries[i]
        if bib.has_co_first(e):
            kept += 1
            continue
        if len(idx) >= 2:                                # co-first needs two or more
            for n in idx:
                e["author"][n]["co-first"] = True
            marked += 1
        elif idx:
            unplaced.append(("only one asterisk placed", i))
    bib.save(entries)
    print(f"co-first authors: {marked} papers marked, {kept} already marked (left as-is)")
    for page, i in sorted(set(unplaced)):
        print(f"   an asterisk couldn't be placed: {i} (on {page})")


if __name__ == "__main__":
    main()
