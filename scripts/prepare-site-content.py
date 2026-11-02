#!/usr/bin/env python3
"""Move the last pieces of the old site into content/, for build-site.py.

Run once. Five things on the old pages weren't in content/ as data yet:

  1. Alumni the roster lists who have no profile (17 of them). Each becomes a
     small file in content/alumni/ marked `profile_page: false`, so the
     generated roster can include them without an empty profile page.
     Alumni whose roster row gives a first job after the lab as well as a
     current one also get `position_after_lab`.
  2. The 57 past rotation students, as content/rotation-students.csv.
  3. The home page's "Selected Publications" and "Perspectives and Reviews",
     which become DOI lists (`featured_publications`, `featured_reviews`) so
     they're drawn from the bibliography in the site's style.
  4. The Google Map on Contact and the Google Calendar on Meetings, which the
     Markdown conversion had dropped.
  5. The News page, whose two-column layout (dates on the left, items on the
     right) the Markdown conversion had flattened into a run of dates followed
     by a run of items. It becomes one "**Month Year** item" line per item.

Safe to re-run: each step is skipped once done.
"""
import csv, html, json, os, re, shutil, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib

ROOT = bib.ROOT
SITE = os.path.join(ROOT, "archive", "site")
CONTENT = os.path.join(ROOT, "content")
ZW = "​﻿"
SECTIONS = {"Graduate Students": "Graduate Student", "Postdoctoral Fellows": "Postdoctoral Scholar",
            "Staff": "Staff", "Undergraduate Students": "Undergraduate Researcher",
            "High school Students": "High School Student"}


def text(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", "".join(c for c in s if c not in ZW)).strip()


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def q(s):
    return json.dumps(s, ensure_ascii=False)


def roster_rows(raw):
    """Every row of the alumni roster's tables, with the role its section implies."""
    start = raw.find('id="wsite-content"')
    heads = sorted((m.start(), role) for title, role in SECTIONS.items()
                   for m in [re.compile(r">[\s" + ZW + r"]*(?:&#8203;)*\s*" + re.escape(title)
                                        + r"\s*(?:&#8203;)*[\s" + ZW + r"]*<").search(raw, start)] if m)
    rows = []
    for m in re.finditer(r'<tr class="wsite-multicol-tr">(.*?)</tr>', raw[start:], re.S):
        cells = [text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", m.group(1), re.S)]
        years_at = next((k for k, c in enumerate(cells) if re.match(r"^\d{4}(\s*[-–]\s*\d{4})?$", c)), None)
        if years_at is None or years_at == 0:
            continue                                    # a header row
        after = [c for c in cells[years_at + 1:] if c]
        page = re.search(r'href="(alumni-+[^"]+\.html)"', m.group(1))
        img = re.search(r'<img[^>]*src="([^"]+)"', m.group(1))
        role = next((r for h, r in reversed(heads) if h < start + m.start()), None)
        rows.append({"name": re.sub(r",\s*(PhD|MD|Ph\.D\.)$", "", cells[years_at - 1]).strip(),
                     "years": cells[years_at], "role": role, "page": page.group(1) if page else None,
                     "photo": img.group(1) if img else "",
                     "now": after[-1] if after else "",
                     "after_lab": after[0] if len(after) >= 2 and after[0] != after[-1] else ""})
    return rows


def step_alumni(raw):
    by_page = {}
    for dirpath, _, files in os.walk(os.path.join(CONTENT, "alumni")):
        for fn in files:
            t = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            mf = bib.header_value(t, "mirror_file")
            if mf:
                by_page[os.path.basename(mf)] = os.path.join(dirpath, fn)
    made = added = 0
    for r in roster_rows(raw):
        if r["page"]:
            path = by_page.get(r["page"])
            if path and r["after_lab"]:
                t = open(path, encoding="utf-8").read()
                if not re.search(r"^position_after_lab:", t, re.M):
                    t = re.sub(r"^(current_position: .*)$",
                               lambda m: m.group(1) + f"\nposition_after_lab: {q(r['after_lab'])}",
                               t, count=1, flags=re.M)
                    open(path, "w", encoding="utf-8").write(t)
                    added += 1
            continue
        slug = slugify(r["name"])
        path = os.path.join(CONTENT, "alumni", slug + ".md")
        if os.path.exists(path):
            continue
        photo = ""
        if r["photo"] and os.path.exists(os.path.join(SITE, r["photo"])):
            ext = os.path.splitext(r["photo"])[1].lower().replace(".jpeg", ".jpg")
            photo = f"images/people/{slug}{ext}"
            os.makedirs(os.path.join(CONTENT, "images", "people"), exist_ok=True)
            shutil.copyfile(os.path.join(SITE, r["photo"]), os.path.join(CONTENT, photo))
        lines = ["---", f"name: {q(r['name'])}", f"role: {q(r['role'] or '')}",
                 f"years_in_lab: {q(r['years'])}", f"current_position: {q(r['now'])}"]
        if r["after_lab"]:
            lines.append(f"position_after_lab: {q(r['after_lab'])}")
        lines += [f"photo: {q(photo)}",
                  "# Listed on the alumni roster only: no profile page of their own.",
                  "profile_page: false", "---", ""]
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        made += 1
    print(f"1. alumni: {made} roster-only files made; position_after_lab added to {added} profiles")


def step_rotation(raw):
    out = os.path.join(CONTENT, "rotation-students.csv")
    if os.path.exists(out):
        print("2. rotation students: already done"); return
    k = raw.find("Past rotation students")
    chunk = raw[k:raw.find('id="footer"')]
    rows = []
    for part in re.split(r"<br\s*/?>", chunk)[1:]:
        page = re.search(r'href="(alumni-+[^"]+\.html)"', part)
        line = text(re.sub(r"<div.*$", "", part, flags=re.S))
        bits = [b.strip() for b in line.split(",")]
        if len(bits) >= 3 and re.search(r"\d{4}$", bits[-1]):
            rows.append({"name": bits[0], "program": ", ".join(bits[1:-1]), "term": bits[-1],
                         "profile": re.sub(r"^alumni-+", "", page.group(1))[:-5] if page else ""})
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["name", "program", "term", "profile"])
        w.writeheader(); w.writerows(rows)
    print(f"2. rotation students: {len(rows)} written to content/rotation-students.csv")


def step_home():
    path = os.path.join(CONTENT, "index.md")
    t = open(path, encoding="utf-8").read()
    if "featured_publications" in t:
        print("3. home page: already done"); return
    E = bib.load()
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    titles = {norm(e.get("title", "")): i for i, e in E.items() if len(norm(e.get("title", ""))) > 20}
    head, body = t[4:].split("\n---\n", 1)

    def take(section, nxt):
        nonlocal body
        m = re.search(r"\*\*" + section + r"\*\*(.*?)(?=\*\*" + nxt + r"\*\*)", body, re.S)
        found, missed = [], []
        for line in m.group(1).split("\n"):
            if len(text(line)) < 30:
                continue
            hit = next((i for k, i in titles.items() if k in norm(text(line))), None)
            (found if hit else missed).append(hit or text(line)[:70])
        key = section.lower().replace(" ", "_")
        body = body[:m.start()] + f"**{section}**\n\n<!-- {key} -->\n\n" + body[m.end():]
        return list(dict.fromkeys(found)), missed

    pubs, miss1 = take("Selected Publications", "Perspectives and Reviews")
    revs, miss2 = take("Perspectives and Reviews", "Highlights from the Lab")
    body = body.replace("<!-- selected_publications -->", "<!-- featured_publications -->") \
               .replace("<!-- perspectives_and_reviews -->", "<!-- featured_reviews -->")
    head += "\nfeatured_publications:\n" + "".join(f"  - {q(i)}\n" for i in pubs).rstrip("\n")
    head += "\nfeatured_reviews:\n" + "".join(f"  - {q(i)}\n" for i in revs).rstrip("\n")
    open(path, "w", encoding="utf-8").write("---\n" + head + "\n---\n" + body)
    print(f"3. home page: {len(pubs)} selected publications, {len(revs)} reviews now drawn from the bibliography")
    for m in miss1 + miss2:
        print(f"   not matched to the bibliography, left out: {m}")


def step_embeds():
    for page, label in (("contact", "map"), ("meetings", "calendar")):
        path = os.path.join(CONTENT, page + ".md")
        t = open(path, encoding="utf-8").read()
        if "<iframe" in t:
            print(f"4. {page}: embed already present"); continue
        raw = open(os.path.join(SITE, page + ".html"), encoding="utf-8").read()
        src = html.unescape(re.search(r'<iframe[^>]*src="([^"]+)"', raw).group(1))
        t = t.rstrip("\n") + (f'\n\n<div class="embed embed-{label}"><iframe src="{html.escape(src)}" '
                              f'title="Google {label}" loading="lazy"></iframe></div>\n')
        open(path, "w", encoding="utf-8").write(t)
        print(f"4. {page}: Google {label} restored")


def inline_md(s):
    """A news item's HTML as Markdown: links, bold and italics kept."""
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
               lambda m: f"[{m.group(2)}]({html.unescape(m.group(1))})", s, flags=re.S)
    s = re.sub(r"</?(?:strong|b)>", "**", s)
    s = re.sub(r"</?(?:em|i)>", "*", s)
    s = "".join(c for c in html.unescape(re.sub(r"<[^>]+>", "", s)) if c not in ZW)
    s = re.sub(r"\*\*(\s*)\*\*", r"\1", s)                # "**January** **2024**"
    return re.sub(r"\s+", " ", s).strip()


def step_news():
    path = os.path.join(CONTENT, "news.md")
    t = open(path, encoding="utf-8").read()
    if re.search(r"^- \*\*", t, re.M):
        print("5. news: already done"); return
    raw = open(os.path.join(SITE, "news.html"), encoding="utf-8").read()
    raw = raw[raw.find('id="wsite-content"'):raw.find('id="footer"')]
    items = []
    for row in re.findall(r'<tr class="wsite-multicol-tr">(.*?)</tr>', raw, re.S):
        dates, texts = [re.findall(r'<div class="paragraph"[^>]*>(.*?)</div>', c, re.S)
                        for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row, re.S)]
        assert len(dates) == len(texts), row[:200]
        items += [(inline_md(d).strip("* "), inline_md(x)) for d, x in zip(dates, texts)]
    head = t[:t.index("\n---\n", 4) + 5]
    body = "".join(f"- **{d}** {x}\n" for d, x in items)
    open(path, "w", encoding="utf-8").write(head + "\n" + body)
    print(f"5. news: {len(items)} items, each with its date")


def main():
    raw = open(os.path.join(SITE, "lab-alumni.html"), encoding="utf-8").read()
    step_alumni(raw)
    step_rotation(raw)
    step_home()
    step_embeds()
    step_news()


if __name__ == "__main__":
    main()
