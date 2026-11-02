#!/usr/bin/env python3
"""Convert the profiles migrated from Weebly to the new profile format.

Run once. The 73 profiles in content/current-members/ and content/alumni/
started as text extracted from the old site's pages; this rewrites each in the
shape of intake/profile-template.md, so old and new members look alike to the
rebuilt site. It reads three sources:

  - the profile's text: name, role, co-mentors, research summary, bio,
    education, and links written into the page
  - the profile's page in site/: the email behind its email icon
  - the alumni roster (site/lab-alumni.html): each alumnus's photo and
    current position, the only record of either for most older alumni

Headshots are copied to content/images/people/. Publication lists, years in
the lab, and where each profile came from (source_url, mirror_file) carry
over unchanged. Anything that couldn't be filled in, or that looked unusual,
is listed in capture/profile-conversion.csv for review.

Profiles already in the new format (they have a `name:` field) are skipped.
Pass --out DIR to write everything under DIR instead, for a preview.
"""
import argparse, csv, html, json, os, re, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib
from extract import ROOT

ZW = "​﻿"
MARKERS = re.compile(r"<!--\s*publications:start.*?<!--\s*publications:end\s*-->\n?", re.S)
ROLES = {r.lower(): r for r in ("Graduate Student", "Postdoctoral Scholar", "Lab Technician",
         "Principal Investigator", "Specialist", "Research Scientist", "Staff Research Associate",
         "Lab Manager", "Undergraduate Researcher", "Visiting Scholar", "Rotation Student")}
PUB_HEADING = re.compile(r"^(?:#+\s*)?(?:\*\*)?[^*]*publications[^*]*(?:\*\*)?$", re.I)
EDU_HEADING = re.compile(r"^\*\*\s*(education|qualifications)\s*\*\*$", re.I)
IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def clean(s):
    return re.sub(r"\s+", " ", "".join(c for c in s if c not in ZW)).strip()


def plain(s):
    """Markdown line -> visible text."""
    s = LINK.sub(lambda m: m.group(1), s)
    return clean(re.sub(r"[*_`]", "", s))


def drop_empty_links(s):
    """Weebly leaves invisible links such as [​​﻿](index.html) around names."""
    return re.sub(r"\[(?:\*\*)?[\s" + ZW + r"*]*(?:\*\*)?\]\([^)]*\)", "", s)


def header(text):
    head, _, body = text[4:].partition("\n---\n")
    return head, body


# The alumni roster's sections, and the role each implies (None: unclear)
SECTIONS = {"Graduate Students": "Graduate Student", "Postdoctoral Fellows": "Postdoctoral Scholar",
            "Staff": None, "Undergraduate Students": "Undergraduate Researcher",
            "High school Students": "High School Student", "Past rotation students": "Rotation Student"}


def roster(site):
    """{profile page: {photo, position, role, section, program, term}} from the roster."""
    raw = open(os.path.join(site, "lab-alumni.html"), encoding="utf-8").read()
    start = raw.find('id="wsite-content"')
    heads = []
    for title, role in SECTIONS.items():
        m = re.compile(r">[\s" + ZW + r"]*(?:&#8203;)*\s*" + re.escape(title) + r"\s*(?:&#8203;)*[\s" + ZW + r"]*<").search(raw, start)
        if m:
            heads.append((m.start(), title, role))
    heads.sort()
    section_at = lambda pos: next(((t, r) for h, t, r in reversed(heads) if h < pos), (None, None))

    out = {}
    for row in re.finditer(r'<tr class="wsite-multicol-tr">(.*?)</tr>', raw, re.S):
        page = re.search(r'href="(alumni-+[^"]+\.html)"', row.group(1))
        if not page:
            continue
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", row.group(1), re.S)
        img = re.search(r'<img[^>]*src="([^"]+)"', row.group(1))
        texts = [t for t in (clean(html.unescape(re.sub(r"<[^>]+>", " ", c))) for c in cells) if t]
        title, role = section_at(row.start())
        out[page.group(1)] = {"photo": img.group(1) if img else "",
                              "position": re.sub(r"\s+(Lab Page|Lab Website|Website)$", "", texts[-1], flags=re.I) if len(texts) >= 3 else "",
                              "role": role, "section": title, "program": "", "term": ""}
    # rotation students: "Name, Program, Term Year" lines, the name a link
    rot = next((h for h, t, _ in heads if t == "Past rotation students"), None)
    if rot is not None:
        for m in re.finditer(r'<a href="(alumni-+[^"]+\.html)"[^>]*>.*?</a>\s*,([^<]*)', raw[rot:], re.S):
            if m.group(1) in out:
                continue
            parts = [clean(html.unescape(x)) for x in m.group(2).split(",") if clean(html.unescape(x))]
            out[m.group(1)] = {"photo": "", "position": "", "role": "Rotation Student",
                               "section": "Past rotation students",
                               "program": parts[0] if parts else "", "term": parts[-1] if len(parts) > 1 else ""}
    return out


def name_tokens(name):
    return {t for t in re.split(r"[^a-z]+", name.lower()) if len(t) > 2}


def check_email(email, name, everyone):
    """Drop an email that's evidently another member's (a page copied from
    theirs); flag one that matches nobody, to confirm by hand."""
    local = re.sub(r"[^a-z]", " ", email.split("@")[0].lower())
    if not email or name_tokens(name) & set(local.split()) or any(t in local for t in name_tokens(name)):
        return email, None
    for other in everyone:
        if other != name and len(name_tokens(other) & set(local.split())) >= 2:
            return "", f"email on the page is {other}'s ({email}) -- dropped"
    return email, f"email {email} doesn't match the name -- confirm it's theirs"


def page_email(site, page):
    if not page or not os.path.exists(os.path.join(ROOT, page)):
        return ""
    raw = open(os.path.join(ROOT, page), encoding="utf-8").read()
    i, j = raw.find('id="wsite-content"'), raw.find('id="footer"')
    m = re.search(r'href="mailto:([^"?]+)', raw[i:j])
    return m.group(1).strip() if m else ""


def convert(path, site, alumni_roster):
    text = open(path, encoding="utf-8").read()
    head, body = header(text)
    if re.search(r"^name:", head, re.M):
        return None, None                                  # already converted
    notes = []
    title = bib.header_value(text, "title") or ""
    m = re.match(r"^(?:Current|Alumni)\s*-+\s*(.+?)\s*-\s*KORTEMME", title)
    title_name = m.group(1).strip() if m else ""
    page = bib.header_value(text, "mirror_file") or ""
    is_alum = os.sep + "alumni" + os.sep in path

    body = MARKERS.sub("", body)
    lines = [drop_empty_links(l).rstrip() for l in body.split("\n")]

    # --- name: the bold line at the top, which can spill onto the next line --
    name, i, affiliation = "", 0, []
    while i < len(lines) and not clean(lines[i]):
        i += 1
    if i < len(lines) and lines[i].lstrip().startswith(("**", "[**")):
        first = lines[i]
        m = re.match(r"^\[\*\*(.+?)\*\*\]\(([^)]+)\)(.*)$", first.strip())        # linked name
        if m:
            name, rest = plain(m.group(1)), m.group(3)
            lines[i] = ""
            if clean(rest):
                affiliation.append(rest.strip())
            notes.append(f"name was a link (to {m.group(2)}); link dropped")
        elif first.count("**") == 1:                     # "**Tanja Kortemme" / "**Principal…"
            name = plain(first)
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            lines[i], lines[i + 1] = "", re.sub(r"^[\s" + ZW + r"]*\*\*", "", nxt)
        else:
            m = re.match(r"^\*\*(.+?)\*\*(.*)$", first.strip())
            name, rest = plain(m.group(1)), m.group(2)
            lines[i] = rest
    if not name:
        name = title_name
    elif title_name and name != title_name:
        notes.append(f"name on page '{name}' differs from old title '{title_name}' (page name used)")

    # --- walk the rest ---------------------------------------------------------
    role, co_mentors, photo_src, links, education, kept = "", [], "", {}, [], []
    in_edu, edu_gap = False, False
    degree = re.compile(r"\b(Bachelor|Master|Ph\.?\s?D|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?D\.?|Diplom|Vordiplom|Doctor|Habilitation)", re.I)
    edu_label = ""                                    # e.g. "**Postdoctoral work**" inside education
    for ln in lines:
        if re.match(r"^\s*([-*_])(\s*\1){2,}\s*$", ln):    # a horizontal rule: just a divider
            ln = ""
        p = plain(ln)
        if in_edu and not IMAGE.search(ln) and not (PUB_HEADING.match(p.strip()) and len(p) < 70):
            if not p:
                edu_gap = bool(education)                 # a gap, but not yet an end
                continue
            sub = re.match(r"^\*\*(.+)\*\*$", clean(ln))
            if sub:
                edu_label = plain(sub.group(1))
                continue
            if edu_label:
                education.append(f"{edu_label}: {p.lstrip('-• ').strip()}")
                edu_label, edu_gap = "", False
                continue
            is_item = ln.lstrip().startswith(("-", "•"))
            if is_item or (degree.search(p) and not (edu_gap and not is_item and len(p) > 120)):
                education.append(p.lstrip("-• ").strip())
                edu_gap = False
                continue
            in_edu = False                                # prose: the section is over
        if not p and not IMAGE.search(ln):
            kept.append("")
            continue
        if PUB_HEADING.match(p.strip()) and len(p) < 70:
            in_edu = False
            continue
        if EDU_HEADING.match(clean(ln)) or re.match(r"^(education|qualifications)$", p, re.I):
            in_edu, edu_gap = True, False
            continue
        img = IMAGE.search(ln)
        if img:
            photo_src = photo_src or img.group(1)
            in_edu = False
            continue
        if not role and p.lower() in ROLES:
            role = ROLES[p.lower()]
            continue
        cm = re.match(r"^co-mentored by\s+(.+)$", p, re.I)
        if cm:
            co_mentors += [clean(x) for x in re.split(r",|\band\b", cm.group(1)) if clean(x)]
            continue
        # a line that is nothing but links: GitHub, website, UCSF profile...
        only_links = LINK.findall(ln)
        if only_links and not clean(LINK.sub("", ln)).strip(", "):
            for label, href in only_links:
                host = re.sub(r"^https?://(www\.)?", "", href.lower()).split("/")[0]
                if host == "github.com":
                    links["github"] = href
                elif "profiles.ucsf.edu" in href:
                    links["ucsf_profile"] = href
                elif "orcid" in href:
                    links["orcid"] = href
                elif "scholar.google" in href:
                    links["scholar"] = href
                else:
                    links["website"] = href
            continue
        if re.match(r"^visiting from\b", p, re.I):         # an affiliation, not research
            affiliation.append(ln.strip())
            continue
        if re.search(r"\(at\)", p):                       # "kortemme (at) cgl.ucsf.edu"
            notes.append(f"dropped spelled-out email line '{p}' (email field used instead)")
            continue
        kept.append("".join(c for c in ln if c not in ZW).strip())

    # --- summary and bio ----------------------------------------------------------
    paras, cur = [], []
    for ln in kept:
        if ln.strip():
            cur.append(ln)
        elif cur:
            paras.append("\n".join(cur)); cur = []
    if cur:
        paras.append("\n".join(cur))
    summary = ""
    if paras:
        first = plain(paras[0])
        italic_only = paras[0].strip().startswith("*") and paras[0].strip().endswith("*")
        if first and len(first) <= 400 and "\n" not in paras[0] and not italic_only:
            summary = first
            paras = paras[1:]
        else:
            notes.append("no short research summary found -- summary left empty")
    bio = "\n\n".join(["\n".join(affiliation)] * bool(affiliation) + paras).strip()

    # --- photo -----------------------------------------------------------------------
    r = alumni_roster.get(os.path.basename(page), {})
    position, program = r.get("position", ""), r.get("program", "")
    if not photo_src and r.get("photo"):
        photo_src = r["photo"]
        notes.append("photo taken from the alumni roster")
    if not role and r.get("role"):
        role = r["role"]
        notes.append(f"role from the roster's '{r['section']}' section")
    elif not role and r.get("section"):
        notes.append(f"listed under '{r['section']}' on the roster; exact role unknown")
    if r.get("term"):
        notes.append(f"rotated {r['term']}")
    if affiliation and not role:
        notes.append(f"affiliation kept in bio: {plain(affiliation[0])[:60]}")
    if not photo_src:
        notes.append("no photo")
    if not role:
        notes.append("no role found")
    if not education:
        notes.append("no education listed")

    years = bib.header_value(text, "years_in_lab") or ""
    if not years:
        notes.append("years in the lab unknown")
    email, problem = check_email(page_email(site, page), name, EVERYONE)
    if problem:
        notes.append(problem)
    return {
        "slug": os.path.basename(path)[:-3], "name": name, "role": role, "years": years,
        "program": program,
        "position": position if is_alum else None, "co_mentors": co_mentors, "summary": summary,
        "photo_src": photo_src, "email": email, "links": links, "education": education,
        "publications": bib.header_list(text, "publications") or [], "bio": bio,
        "source_url": bib.header_value(text, "source_url") or "", "mirror_file": page,
    }, notes


def q(s):
    return json.dumps(s or "", ensure_ascii=False)


def render(p, photo_rel):
    out = ["---",
           f"name: {q(p['name'])}",
           'pronouns: ""',
           f"role: {q(p['role'])}",
           f"program: {q(p['program'])}",
           f"years_in_lab: {q(p['years'])}"]
    if p["position"] is not None:
        out.append(f"current_position: {q(p['position'])}")
    out += [f"co_mentors: {json.dumps(p['co_mentors'], ensure_ascii=False)}",
            f"summary: {q(p['summary'])}",
            f"photo: {q(photo_rel)}",
            f"email: {q(p['email'])}",
            "links:"]
    for k in ("orcid", "scholar", "website", "github"):
        out.append(f"  {k}: {q(p['links'].get(k, ''))}")
    for k, v in p["links"].items():
        if k not in ("orcid", "scholar", "website", "github"):
            out.append(f"  {k}: {q(v)}")
    out += (["education:"] + [f"  - {q(e)}" for e in p["education"]]) if p["education"] else ["education: []"]
    out += (["publications:"] + [f"  - {q(d)}" for d in p["publications"]]) if p["publications"] else ["publications: []"]
    out += ["# Where this profile came from: the old Weebly site.",
            f"source_url: {q(p['source_url'])}",
            f"mirror_file: {q(p['mirror_file'])}",
            "---", ""]
    return "\n".join(out) + (p["bio"] + "\n" if p["bio"] else "")


def main():
    ap = argparse.ArgumentParser(description="Convert migrated profiles to the new format.")
    ap.add_argument("--out", help="write under this folder instead of in place (a preview)")
    args = ap.parse_args()
    dest_root = os.path.abspath(args.out) if args.out else ROOT
    global EVERYONE
    site = os.path.join(ROOT, "site")
    alumni_roster = roster(site)
    EVERYONE = []                                   # every member's name, for the email check
    for folder in ("current-members", "alumni"):
        for fn in os.listdir(os.path.join(ROOT, "content", folder)):
            t = open(os.path.join(ROOT, "content", folder, fn), encoding="utf-8").read()
            m = re.match(r"^(?:Current|Alumni)\s*-+\s*(.+?)\s*-\s*KORTEMME", bib.header_value(t, "title") or "")
            if m:
                EVERYONE.append(m.group(1).strip())

    report, done = [], 0
    for folder in ("current-members", "alumni"):
        for fn in sorted(os.listdir(os.path.join(ROOT, "content", folder))):
            if not fn.endswith(".md"):
                continue
            src = os.path.join(ROOT, "content", folder, fn)
            p, notes = convert(src, site, alumni_roster)
            if p is None:
                continue
            photo_rel = ""
            if p["photo_src"]:
                from_path = os.path.join(site, p["photo_src"])
                ext = os.path.splitext(from_path)[1].lower().replace(".jpeg", ".jpg")
                photo_rel = f"images/people/{p['slug']}{ext}"
                if os.path.exists(from_path):
                    os.makedirs(os.path.join(dest_root, "content", "images", "people"), exist_ok=True)
                    shutil.copyfile(from_path, os.path.join(dest_root, "content", photo_rel))
                else:
                    notes.append(f"photo file missing: site/{p['photo_src']}")
                    photo_rel = ""
            out_path = os.path.join(dest_root, "content", folder, fn)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as fh:
                fh.write(render(p, photo_rel))
            done += 1
            report.append({"profile": f"{folder}/{p['slug']}", "name": p["name"], "role": p["role"],
                           "years_in_lab": p["years"], "current_position": p["position"] or "",
                           "photo": photo_rel, "email": "yes" if p["email"] else "",
                           "education": len(p["education"]), "papers": len(p["publications"]),
                           "summary": p["summary"][:80], "notes": "; ".join(notes)})

    os.makedirs(os.path.join(dest_root, "capture"), exist_ok=True)
    rep = os.path.join(dest_root, "capture", "profile-conversion.csv")
    with open(rep, "w", newline="", encoding="utf-8") as fh:
        if report:
            w = csv.DictWriter(fh, fieldnames=list(report[0]))
            w.writeheader()
            w.writerows(report)
    print(f"converted {done} profiles; report: {os.path.relpath(rep, dest_root) if args.out else 'capture/profile-conversion.csv'}")


if __name__ == "__main__":
    main()
