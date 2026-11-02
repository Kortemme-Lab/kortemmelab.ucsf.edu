#!/usr/bin/env python3
"""Copy each alumnus's years in the lab from the roster into their own file.

The live site keeps those years only on the Lab Alumni roster
(archive/site/lab-alumni.html), not on anyone's profile. This adds them to each
alumnus's Markdown as a `years_in_lab` frontmatter field, so the information
travels with the person's file.

The roster is a table with one row per person: photo, name, years, position.
A row counts only if it links to exactly one profile and has exactly one
years cell; anything else is reported rather than guessed at.

Hand edits win: a file that already has `years_in_lab` is never changed.
Run after extract.py. Idempotent.
"""
import html, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import ROOT, content_index, content_path

ROSTER = os.path.join(ROOT, "archive", "site", "lab-alumni.html")
FIELD = "years_in_lab"
YEARS_RE = re.compile(r"^\d{4}(?:\s*[-–—]\s*(?:\d{4}|present|now))?$", re.I)
PROFILE_RE = re.compile(r'href="(alumni-+[^"]+)\.html"')


def cell_text(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s.replace("​", "").replace("﻿", "")).strip()


def roster_years():
    """{profile slug: years} from the roster, plus rows that didn't parse."""
    page = open(ROSTER, encoding="utf-8").read()
    years, unclear = {}, []
    for row in re.findall(r'<tr class="wsite-multicol-tr">(.*?)</tr>', page, re.S):
        cells = [cell_text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]
        found = [c for c in cells if YEARS_RE.match(c)]
        people = sorted(set(PROFILE_RE.findall(row)))
        if not found or not people:
            continue              # header rows, and alumni without a profile page
        if len(people) != 1 or len(found) != 1:
            unclear.append(f"{people} {found}")
            continue
        years[people[0]] = found[0]
    return years, unclear


EMPTY_RE = re.compile(rf'^{FIELD}:[ \t]*(?:""|\'\')?[ \t]*$', re.M)


def add_field(path, value):
    """Fill in the field; False if it already has a value (hand edits win)."""
    text = open(path, encoding="utf-8").read()
    head, sep, rest = text.partition("\n---\n")
    if EMPTY_RE.search(head):                         # present but empty: fill it
        head = EMPTY_RE.sub(f"{FIELD}: {json.dumps(value)}", head, count=1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(head + sep + rest)
        return True
    if re.search(rf"^{FIELD}:", head, re.M):
        return False
    # after `title:` in an old-format file, after `name:` in a profile
    head = re.sub(r"^((?:title|name): .*)$", lambda m: f"{m.group(1)}\n{FIELD}: {json.dumps(value)}",
                  head, count=1, flags=re.M)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(head + sep + rest)
    return True


def main():
    years, unclear = roster_years()
    index = content_index()
    added = kept = 0
    missing = []
    for slug, value in sorted(years.items()):
        path = os.path.join(ROOT, content_path(slug, index))
        if not os.path.exists(path):
            missing.append(slug)
        elif add_field(path, value):
            added += 1
        else:
            kept += 1

    alumni_dir = os.path.join(ROOT, "content", "alumni")
    without = sorted(
        fn[:-3] for fn in os.listdir(alumni_dir)
        if fn.endswith(".md") and (EMPTY_RE.search(open(os.path.join(alumni_dir, fn), encoding="utf-8").read())
                                   or not re.search(rf"^{FIELD}:", open(os.path.join(alumni_dir, fn),
                                                                        encoding="utf-8").read(), re.M)))

    print(f"roster: {len(years)} alumni with a profile and years")
    print(f"{FIELD}: {added} added, {kept} already present (left as-is)")
    if without:
        print(f"alumni/ files with no {FIELD} (not on the roster): {', '.join(without)}")
    if missing:
        print(f"on the roster but no content file: {', '.join(missing)}")
    if unclear:
        print("roster rows skipped as ambiguous:")
        for u in unclear:
            print("   ", u)


if __name__ == "__main__":
    main()
