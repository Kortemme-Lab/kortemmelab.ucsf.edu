#!/usr/bin/env python3
"""Add new lab members from the intake form's responses.

    python3 scripts/add-person.py --csv intake/responses.csv
    python3 scripts/add-person.py --csv intake/responses.csv --dry-run
    python3 scripts/add-person.py --csv intake/responses.csv --only "Jane Doe" --photo ~/jane.jpg
    python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip
    python3 scripts/add-person.py --add-papers "Jane Doe" --dois "10.1126/science.abc0881"

Three ways in. --zip takes the file saved by the profile form
(intake/profile-form.html, also at docs/profile-form.html): a new profile is
checked and filed, and an update (made in the form's "Update my profile"
mode) is merged into the existing profile, keeping anything the form doesn't
edit; someone whose update gives an end year moves to content/alumni/.
--add-papers adds DOIs to an existing profile, found by name. --csv takes the
responses exported from a Google or Microsoft form instead, as below.

For each response (the questions are in intake/form-questions.md) this writes
content/current-members/<first-last>.md in the shape of
intake/profile-template.md, files their headshot under content/images/people/,
gathers their publications, and then runs render-publications.py to draw the
list.

Publications come from two places, either or both:
  - their ORCID iD: every article, preprint, chapter and conference paper on
    their public ORCID record (if they asked for publications from before
    they joined -- for a new member, that's nearly all of them)
  - DOIs (or arXiv IDs) typed into the form, for anyone without an ORCID or
    for papers ORCID is missing
Every DOI is looked up before anything is written; ones that don't resolve
are reported and left out rather than breaking the page.

Someone already in content/ -- current, alumni or archived -- is skipped,
never overwritten. Edit their file by hand instead.
"""
import argparse, csv, json, os, re, shutil, struct, subprocess, sys, tempfile, unicodedata, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bibliography as bib
from extract import ROOT, content_index

PEOPLE_DIR = os.path.join(ROOT, "content", "current-members")
PHOTO_DIR = os.path.join(ROOT, "content", "images", "people")
DEFAULT_PHOTOS = os.path.join(ROOT, "intake", "photos")

# Each answer is found by how its column title begins (intake/form-questions.md).
QUESTIONS = {
    "name": "full name", "pronouns": "pronouns", "role": "role in the lab",
    "program": "graduate program", "year": "year you joined", "co_mentors": "co-mentors",
    "summary": "research summary", "bio": "longer bio", "education": "education",
    "photo": "headshot", "email": "lab email", "show_email": "show my email",
    "orcid": "orcid", "earlier": "include publications from before", "dois": "dois",
    "scholar": "google scholar", "website": "personal website", "github": "github",
}
REQUIRED = ("name",)
# ORCID work types that belong in a publication list (not datasets, talks...)
ORCID_TYPES = {"journal-article", "preprint", "conference-paper", "book-chapter", "book",
               "review", "working-paper", "report"}
IMAGE_EXT = {".jpg": ".jpg", ".jpeg": ".jpg", ".png": ".png", ".webp": ".webp"}
MIN_PIXELS = 400
# What a form .zip may hold: the profile, and a headshot with the same name.
ZIP_PROFILE = re.compile(r"^content/(current-members|alumni)/([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
ZIP_MANIFEST = "submission.json"         # {"kind": "update", "slug": ...} from the form's update mode
ZIP_PHOTO = re.compile(r"^content/images/people/([a-z0-9]+(?:-[a-z0-9]+)*)\.(jpg|png|webp)$")
ZIP_IGNORED = re.compile(r"(^|/)(__MACOSX/|\.DS_Store$)")
ZIP_MAX_BYTES = {"profile": 200_000, "photo": 15_000_000}


# --- reading the form ----------------------------------------------------------
def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def columns(headers):
    found = {}
    for field, start in QUESTIONS.items():
        hits = [h for h in headers if norm(h).startswith(start)]
        if len(hits) > 1:
            sys.exit(f"STOPPED -- more than one column starts with '{start}': {hits}")
        if hits:
            found[field] = hits[0]
    missing = [QUESTIONS[f] for f in REQUIRED if f not in found]
    if missing:
        sys.exit(f"STOPPED -- no column starting with: {', '.join(missing)}\n"
                 "See intake/form-questions.md for the question titles.")
    return found


def yes(s):
    return norm(s).startswith("y")


def split_lines(s, seps=r"[\n;]+"):
    return [x.strip() for x in re.split(seps, s or "") if x.strip()]


def slugify(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def url(s, prefix=""):
    s = (s or "").strip()
    if not s:
        return ""
    if re.match(r"^https?://", s):
        return s
    return (prefix + s.lstrip("@/")) if prefix else "https://" + s


# --- ORCID ------------------------------------------------------------------------
def orcid_id(s):
    """The 16-character iD from whatever was typed, or None if it's invalid."""
    m = re.search(r"(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dXx])", s or "")
    if not m:
        return None
    digits = "".join(m.groups()).upper()
    total = 0
    for ch in digits[:-1]:                                   # ISO 7064 MOD 11-2
        total = (total + int(ch)) * 2
    check = (12 - total % 11) % 11
    if digits[-1] != ("X" if check == 10 else str(check)):
        return None                                          # a typo, most likely
    return "-".join(digits[i:i + 4] for i in range(0, 16, 4))


def orcid_dois(oid):
    """DOIs of the publications on a public ORCID record (None if unreachable)."""
    data = bib._get(f"https://pub.orcid.org/v3.0/{oid}/works", "application/json")
    if data is None:
        return None
    dois = []
    for group in data.get("group", []):
        kind = ((group.get("work-summary") or [{}])[0]).get("type", "").lower()
        for x in (group.get("external-ids") or {}).get("external-id", []):
            if x.get("external-id-type") == "doi" and x.get("external-id-relationship", "self") == "self":
                if kind in ORCID_TYPES:
                    dois.append(bib.clean_doi(x["external-id-value"]))
                break
    return list(dict.fromkeys(dois))


# --- photos -------------------------------------------------------------------------
def image_size(path):
    """(width, height) of a PNG or JPEG, or None if it can't tell."""
    with open(path, "rb") as fh:
        head = fh.read(26)
        if head[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">II", head[16:24])
        if head[:2] != b"\xff\xd8":
            return None
        fh.seek(2)
        while True:
            b = fh.read(1)
            while b and b != b"\xff":
                b = fh.read(1)
            while b == b"\xff":
                b = fh.read(1)
            if not b:
                return None
            marker = b[0]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                continue
            length = struct.unpack(">H", fh.read(2))[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                fh.read(1)
                h, w = struct.unpack(">HH", fh.read(4))
                return w, h
            fh.seek(length - 2, 1)


def find_photo(name, folder):
    """The photo in `folder` whose filename contains this person's name."""
    if not os.path.isdir(folder):
        return None, None
    want = [t for t in slugify(name).split("-") if len(t) > 1]  # skip middle initials
    hits = [f for f in sorted(os.listdir(folder))
            if not f.startswith(".") and all(t in slugify(f).split("-") for t in want)]
    if len(hits) > 1:
        return None, f"more than one photo matches: {', '.join(hits)} -- pass --photo"
    return (os.path.join(folder, hits[0]), None) if hits else (None, None)


def check_photo(path):
    """Problems that stop a photo being used, and ones merely worth a look."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".heic", ".heif"):
        return f"{os.path.basename(path)} is an iPhone HEIC photo, which browsers can't show. " \
               f"Convert it first:  sips -s format jpeg \"{path}\" --out photo.jpg", None
    if ext not in IMAGE_EXT:
        return f"{os.path.basename(path)}: use a JPG or PNG", None
    size = image_size(path)
    if size and min(size) < MIN_PIXELS:
        return None, f"photo is only {size[0]}×{size[1]} px; at least {MIN_PIXELS}×{MIN_PIXELS} looks sharp"
    return None, None


# --- the profile ---------------------------------------------------------------------
def q(s):
    return json.dumps(s or "", ensure_ascii=False)


def profile(p):
    lines = ["---",
             f"name: {q(p['name'])}",
             f"pronouns: {q(p['pronouns'])}",
             f"role: {q(p['role'])}",
             f"program: {q(p['program'])}",
             f"years_in_lab: {q(p['years'])}",
             f"co_mentors: {json.dumps(p['co_mentors'], ensure_ascii=False)}",
             f"summary: {q(p['summary'])}",
             f"photo: {q(p['photo'])}",
             f"email: {q(p['email'])}",
             "links:",
             f"  orcid: {q(p['orcid_url'])}",
             f"  scholar: {q(p['scholar'])}",
             f"  website: {q(p['website'])}",
             f"  github: {q(p['github'])}"]
    lines += ["education:"] + [f"  - {q(e)}" for e in p["education"]] if p["education"] else ["education: []"]
    lines += ["publications:"] + [f"  - {q(d)}" for d in p["publications"]] if p["publications"] else ["publications: []"]
    return "\n".join(lines) + "\n---\n\n" + (p["bio"].strip() + "\n" if p["bio"].strip() else "")


# --- education: one style for degrees ---------------------------------------------------------
# Every entry reads "Degree, Subject, Institution", with the degree abbreviated
# the same way throughout: B.S., B.A., M.S., M.A., M.Sc., Ph.D. German degrees
# keep their name, with the equivalent in brackets: "Dr. rer. nat. (Ph.D.)".
DEGREE_WORDS = [
    (r"bachelors?\s+of\s+science", "B.S."), (r"bachelors?\s+of\s+arts", "B.A."),
    (r"masters?\s+of\s+science", "M.S."), (r"masters?\s+of\s+arts", "M.A."),
    (r"doctor\s+of\s+philosophy", "Ph.D."),
]
DEGREE_SHORT = [                              # bare abbreviations, however punctuated
    (r"b\.?\s?s\.?", "B.S."), (r"b\.?\s?a\.?", "B.A."), (r"m\.?\s?sc\.?", "M.Sc."),
    (r"m\.?\s?s\.?", "M.S."), (r"m\.?\s?a\.?", "M.A."), (r"ph\.?\s?d\.?", "Ph.D."),
]
DEGREE = r"(?:B\.S\.|B\.A\.|M\.Sc\.|M\.S\.|M\.A\.|Ph\.D\.|(?:Vordiplom|Diplom|Dr\. rer\. nat\.)(?: \([^)]*\))?)"


def tidy_degree(entry):
    """One education entry in the site's style; anything unrecognised is left as it is."""
    s = re.sub(r"\s+", " ", entry).strip()
    if re.match(r"(?i)postdoctoral work:", s):
        return s
    for words, short in DEGREE_WORDS:
        s = re.sub(rf"(?i)^{words}\b", short, s)
    s = re.sub(r"(?i)^dr\.?\s?rer\.?\s?nat\.?", "Dr. rer. nat.", s)
    for pat, short in DEGREE_SHORT:          # the degree itself, and one in brackets after it
        s = re.sub(rf"(?i)^{pat}(?=[\s,(]|$)", short, s)
        s = re.sub(rf"(?i)\({pat}\)", f"({short})", s)
    m = re.match(rf"^({DEGREE})\s*\(([^)]+)\),\s*(.+)$", s)
    if m and not re.match(r"^(B\.S\.|B\.A\.|M\.Sc\.|M\.S\.|M\.A\.|Ph\.D\.)$", m.group(2)):
        s = f"{m.group(1)}, {m.group(2)}, {m.group(3)}"   # "M.S. (Biochemistry), X" -> "M.S., Biochemistry, X"
    m = re.match(rf"^({DEGREE}),?\s+(.+)$", s)
    if m:
        s = f"{m.group(1)}, {m.group(2)}"                  # a comma after the degree
    return s


def tidy_education(text):
    """A profile with its education entries in the site's style (nothing else changed)."""
    head, sep, body = text[4:].partition("\n---\n")
    out, inside = [], False
    for ln in head.split("\n"):
        if re.match(r"^education:", ln):
            inside = True
        elif inside and not ln.startswith((" ", "\t")):
            inside = False
        m = re.match(r"^(\s+-\s+)(.+)$", ln) if inside else None
        if m:
            ln = m.group(1) + json.dumps(tidy_degree(bib._scalar(m.group(2))), ensure_ascii=False)
        out.append(ln)
    return text[:4] + "\n".join(out) + sep + body


# --- a .zip from the profile form ----------------------------------------------------------
def read_zip(path):
    """What's in a form .zip: the profile, its photo, and what kind of submission it is.

    Anything else in the file, or a path outside the expected places, stops it:
    the .zip came from outside the lab, so nothing in it is trusted blindly.
    """
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        return None, f"not a readable .zip ({e})"
    profile_name, photo, manifest, problems = None, None, None, []
    with z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir() or ZIP_IGNORED.search(name):
                continue
            m, n = ZIP_PROFILE.match(name), ZIP_PHOTO.match(name)
            if m and not profile_name:
                if info.file_size > ZIP_MAX_BYTES["profile"]:
                    problems.append(f"{name} is too large for a profile")
                profile_name = name
            elif n and not photo:
                if info.file_size > ZIP_MAX_BYTES["photo"]:
                    problems.append(f"{name} is over 15 MB")
                photo = name
            elif name == ZIP_MANIFEST and manifest is None and info.file_size < 10_000:
                manifest = name
            else:
                problems.append(f"unexpected file in the .zip: {name}")
        if not profile_name:
            problems.append("no profile (content/current-members/<name>.md) in the .zip")
        slug = ZIP_PROFILE.match(profile_name).group(2) if profile_name else None
        if photo and slug and ZIP_PHOTO.match(photo).group(1) != slug:
            problems.append(f"the photo's name ({photo}) doesn't match the profile's ({profile_name})")
        kind, info = "new", {}
        if manifest:
            try:
                info = json.loads(z.read(manifest).decode("utf-8"))
                kind = info.get("kind", "new")
                if kind not in ("new", "update") or (kind == "update" and info.get("slug") != slug):
                    problems.append(f"{ZIP_MANIFEST} doesn't match the profile in the .zip")
            except ValueError:
                problems.append(f"{ZIP_MANIFEST} isn't readable")
        if problems:
            return None, "; ".join(problems)
        def pairs(key):                      # [[published, preprint], ...]
            got = info.get(key) or []
            got = got.items() if isinstance(got, dict) else got
            return [(bib.clean_doi(str(x[0])), bib.clean_doi(str(x[1]))) for x in got
                    if isinstance(x, (list, tuple)) and len(x) == 2]
        return {"slug": slug, "kind": kind, "text": z.read(profile_name).decode("utf-8"),
                "photo": (photo, z.read(photo)) if photo else None,
                "replaces": pairs("replaces"), "keeps": pairs("keeps")}, None


def looks_like_image(name, data):
    """The photo really is the kind of image its name says (it came from outside)."""
    ext = os.path.splitext(name)[1].lower()
    magic = {".jpg": b"\xff\xd8", ".png": b"\x89PNG", ".webp": b"RIFF"}
    return data.startswith(magic.get(ext, b"\0\0\0\0"))


def checked_photo(got, notes):
    """The .zip's photo as (file name, bytes) if it can be used, else None."""
    if not got["photo"]:
        return None
    zname, data = got["photo"]
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(zname)[1]) as tmp:
        tmp.write(data)
        tmp.flush()
        stop, warn = check_photo(tmp.name)
    if stop:
        notes.append(stop)
        return None
    if warn:
        notes.append(warn)
    if not looks_like_image(zname, data):
        notes.append(f"{os.path.basename(zname)} isn't a readable JPG or PNG, left out")
        return None
    return os.path.basename(zname), data


def checked_dois(dois, E, notes):
    """The DOIs that resolve (looked up and added to E if new), and how many were new to E."""
    good, added = [], 0
    for d in dict.fromkeys(bib.clean_doi(d) for d in dois):
        if d in E:
            good.append(d)
            continue
        rec = bib.fetch(d)
        if rec:
            E[rec["id"]] = rec
            good.append(rec["id"])
            added += 1
        else:
            notes.append(f"DOI didn't resolve, left out: {d}")
    return good, added


# --- preprints and their published versions ------------------------------------------------------
def preprint_choices(E, added, replaces, keeps, entry, how_to_replace):
    """Apply the member's answers about preprints; flag pairs nobody answered for.

    replaces / keeps: (published DOI, preprint DOI) pairs the member confirmed
    or declined. A replacement is only made if the published paper's own DOI
    record names that preprint, so no one can retire an unrelated paper.
    Returns the preprints now replaced, and whether the bibliography changed.
    """
    named, gone, changed = {}, set(), False
    def preprints(j):
        if j not in named:
            named[j] = bib.preprints_of(j)
        return named[j]
    answered = set(replaces) | set(keeps)
    for j, p in replaces:
        if j not in added:
            continue
        if p not in E:
            continue                                  # not on the website: nothing to replace
        if p not in preprints(j):
            entry["notes"].append(f"not replaced: {j}'s DOI record doesn't name {p} as its preprint "
                                  "(a website manager can link them by hand)")
            continue
        bib.link_preprint(E, p, j)
        gone.add(p)
        changed = True
        entry.setdefault("replaces", []).append({"published": j, "preprint": p,
                                                 "title": bib.plain(E[p].get("title", ""))})
    for j, p in keeps:
        if j in added and p in E:
            bib.keep_preprint(E, p, j)
            changed = True
            entry["notes"].append(f"kept both, as asked: the preprint {p} and its published version {j}")
    for j in added:                                   # pairs the member wasn't asked about
        for p in preprints(j):
            if p in E and (j, p) not in answered and bib.published_version(E[p]) != j:
                entry["notes"].append(f"{j} is the published version of the preprint "
                                      f"\"{bib.plain(E[p].get('title', ''))}\" ({p}), which stays listed. "
                                      + how_to_replace)
    if gone:
        n = len(gone)
        entry["changes"].append(f"{n} preprint{'s' * (n != 1)} replaced by {'their' if n != 1 else 'its'} "
                                "published version")
    return gone, changed


# --- merging an update into an existing profile -----------------------------------------------
# The fields the profile form edits. Anything else in a profile's header (an
# extra link, where it came from, profile_page: false, comments) is kept.
MANAGED = ["name", "pronouns", "role", "program", "years_in_lab", "current_position",
           "position_after_lab", "co_mentors", "summary", "photo", "email", "links",
           "education", "publications"]
FORM_LINKS = ["orcid", "scholar", "website", "github"]
ALUMNI_ONLY = ("current_position", "position_after_lab")     # not removed if the form leaves them out
LABELS = {"years_in_lab": "years in the lab", "current_position": "current position",
          "position_after_lab": "position after the lab", "co_mentors": "co-mentors",
          "summary": "research summary", "photo": "photo", "email": "email"}


def split_profile(text):
    head, _, body = text[4:].partition("\n---\n")
    return head, body


def blocks(head):
    """The header as [key, comment lines, field lines], in order."""
    out, comments = [], []
    for ln in head.split("\n"):
        m = re.match(r"^([\w-]+):", ln)
        if m:
            out.append([m.group(1), comments, [ln]])
            comments = []
        elif ln.startswith((" ", "\t")) and out and not comments:
            out[-1][2].append(ln)
        else:
            comments.append(ln)
    if comments:
        out.append([None, comments, []])
    return out


def merge_links(old_lines, new_lines):
    """links: the form's four from the update, any others (ucsf_profile...) as they were."""
    sub = lambda lines: {re.match(r"^\s+([\w-]+):", l).group(1): l for l in lines[1:]
                         if re.match(r"^\s+([\w-]+):", l)}
    old, new = sub(old_lines), sub(new_lines)
    keys = list(old) + [k for k in new if k not in old]
    return ["links:"] + [new[k] if k in FORM_LINKS and k in new else old[k] if k in old else new[k]
                         for k in keys]


def merge_profile(old_text, new_text, keep_photo):
    """The existing profile with the form's fields replaced; and what changed."""
    oh, ob = split_profile(old_text)
    nh, nb = split_profile(new_text)
    new = {k: lines for k, _, lines in blocks(nh) if k}
    out, done, changes = [], set(), []
    for key, comments, lines in blocks(oh):
        if key in MANAGED and key in new and not (key == "photo" and keep_photo):
            repl = merge_links(lines, new[key]) if key == "links" else new[key]
            if repl != lines and key not in ("publications", "photo"):
                changes.append(LABELS.get(key, key.replace("_", " ")))
            lines = repl
        done.add(key)
        out += comments + lines
    for key in MANAGED:                       # fields the old file didn't have yet
        if key in new and key not in done and not (key == "photo" and keep_photo):
            at = next((i for i, l in enumerate(out) if l.startswith("publications:")), len(out))
            out[at:at] = new[key]
            changes.append(LABELS.get(key, key.replace("_", " ")))
    intro, sep, pubs = ob.partition("## Publications")
    bio = nb.strip()
    if bio != intro.strip():
        changes.append("bio")
    body = "\n" + (bio + "\n\n" if bio else "") + (sep + pubs if sep else "")
    return "---\n" + "\n".join(out) + "\n---\n" + body.rstrip("\n") + "\n", changes


# --- adding or updating from a .zip --------------------------------------------------------------
def link_value(text, key):
    """One of the profile's links (they sit indented under `links:`)."""
    head = split_profile(text)[0]
    m = re.search(rf"(?m)^\s+{re.escape(key)}:[ \t]*(.+)$", head)
    return bib._scalar(m.group(1)) if m else ""


def left_lab(text):
    return bool(re.search(r"\d{4}\s*-\s*\d{4}", bib.header_value(text, "years_in_lab") or ""))


def add_from_zips(paths, dry_run, no_render, report_path=None, expect=None):
    E, existing = bib.load(), content_index()
    changed, bib_added, report, bib_dirty = [], 0, [], False

    def skip(entry, why):
        print(f"   skipped: {why}")
        entry.update(status="skipped", problem=why)

    for path in paths:
        print(f"\n== {os.path.basename(path)}")
        entry = {"file": os.path.basename(path), "status": "ok", "problem": "", "notes": [], "changes": []}
        report.append(entry)
        got, problem = read_zip(os.path.expanduser(path))
        if problem:
            skip(entry, problem)
            continue
        slug, text, notes, kind = got["slug"], tidy_education(got["text"]), entry["notes"], got["kind"]
        name = bib.header_value(text, "name")
        entry.update(kind=kind, slug=slug, name=name or "", role=bib.header_value(text, "role") or "")
        if not text.startswith("---\n") or not name:
            skip(entry, "the profile has no header with a name; was it made by the profile form?")
            continue
        if expect and kind != expect:
            skip(entry, "this .zip is an update to an existing profile; attach it to an *Update my profile* issue"
                 if kind == "update" else
                 "this .zip is a new profile, not an update; in the profile form, choose *Update my profile* "
                 "and load your current profile first")
            continue
        here = [p for p in existing.get(f"{slug}.md", []) if "/archive/" not in p]
        if kind == "new" and existing.get(f"{slug}.md"):
            skip(entry, f"someone called {name} is already on the website ({existing[f'{slug}.md'][0]}); "
                        "to change that profile, use *Update my profile* instead")
            continue
        if kind == "update" and not here:
            skip(entry, f"there's no profile called {slug}.md on the website to update")
            continue

        good, n = checked_dois(bib.header_list(text, "publications") or [], E, notes)
        bib_added += n
        here_text = open(os.path.join(ROOT, here[0]), encoding="utf-8").read() if kind == "update" else ""
        before = [d.lower() for d in bib.header_list(here_text, "publications") or []] if here_text else []
        gone, relinked = preprint_choices(
            E, [d for d in good if d not in before], got["replaces"], got["keeps"], entry,
            "To show only the published paper, answer the profile form's question about it and attach the new .zip.")
        bib_dirty = bib_dirty or relinked
        good = [d for d in good if d not in gone]     # this person's list loses them too
        photo = checked_photo(got, notes)
        entry["photo"] = photo[0] if photo else ""
        if photo:
            text = re.sub(r'(?m)^photo: .*$', f'photo: "images/people/{photo[0]}"', text, count=1)

        if kind == "new":
            dest = f"content/{'alumni' if left_lab(text) else 'current-members'}/{slug}.md"
            final = text
            entry["changes"] = ["new profile"] + entry["changes"]
            if not photo:
                final = re.sub(r'(?m)^photo: .*$', 'photo: ""', final, count=1)
                notes.append(f"no headshot -- later, save one as content/images/people/{slug}.jpg"
                             f' and set photo: "images/people/{slug}.jpg" in their file')
        else:
            src = here[0]
            old = open(os.path.join(ROOT, src), encoding="utf-8").read()
            old_photo = bib.header_value(old, "photo") or ""
            old_pubs = [d.lower() for d in bib.header_list(old, "publications") or []]
            final, merged = merge_profile(old, text, keep_photo=not photo)
            entry["changes"] = merged + entry["changes"]
            plus, minus = len(set(good) - set(old_pubs)), len(set(old_pubs) - set(good) - gone)
            if plus or minus:
                entry["changes"].append(" and ".join(x for x in (f"{plus} paper{'s' * (plus != 1)} added" if plus else "",
                                                                 f"{minus} removed" if minus else "") if x))
            if photo:
                entry["changes"].append("new photo")
            dest = src
            if src.startswith("content/current-members/") and left_lab(final):
                dest = f"content/alumni/{slug}.md"
                entry["changes"].append("moved to Lab Alumni")
            if re.search(r"(?m)^profile_page:\s*false", split_profile(old)[0]):
                notes.append("this alumnus is on the roster only, with no page of their own "
                             "(profile_page: false); delete that line to give them a profile page")
            if not entry["changes"]:
                skip(entry, "nothing in this .zip differs from the profile already on the website")
                continue
            entry["old_photo"] = old_photo
        # For the identity check: the GitHub account already on the profile, not
        # the one in the submission (which anyone could set to their own).
        entry.update(path=dest, publications=len(good),
                     github=link_value(old if kind == "update" else final, "github"))
        print(f"   {name}: {', '.join(entry['changes'])} -> {dest}")

        if not dry_run:
            if kind == "update" and dest != src:
                os.remove(os.path.join(ROOT, src))
            full = os.path.join(ROOT, dest)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as fh:
                fh.write(final)
            if [d.lower() for d in bib.header_list(final, "publications") or []] != good:
                bib.set_list(full, "publications", good)      # leaves out DOIs that didn't resolve
            if photo:
                os.makedirs(PHOTO_DIR, exist_ok=True)
                with open(os.path.join(PHOTO_DIR, photo[0]), "wb") as fh:
                    fh.write(photo[1])
                stale = entry.get("old_photo", "")
                if stale and stale != f"images/people/{photo[0]}" and stale.startswith("images/people/") \
                        and os.path.isfile(os.path.join(ROOT, "content", stale)):
                    os.remove(os.path.join(ROOT, "content", stale))    # the photo it replaces
            changed.append(slug)
            print(f"   wrote {dest}" + (f" and content/images/people/{photo[0]}" if photo else ""))
        for n in notes:
            print(f"   note: {n}")
    finish(report, report_path, dry_run, no_render, changed, bib_added, E, bib_dirty)


def finish(report, report_path, dry_run, no_render, changed, bib_added, E, bib_dirty=False):
    if report_path:                         # for .github/workflows/profile-submission.yml
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
    if dry_run:
        print("\nDry run: nothing was written.")
        return
    if bib_added or bib_dirty:
        bib.save(E)
    print(f"\n{len(changed)} profiles added or updated; {bib_added} new papers in the bibliography")
    if changed and not no_render:
        print("drawing their publication lists...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "render-publications.py")],
                       check=False)
    if changed:
        print("\nNext: python3 scripts/build-site.py, look at their page, then commit and push.")


# --- the quick lane: new papers for an existing profile ----------------------------------------------
def name_key(s):
    return slugify(s).replace("-", "")


def find_profile(name):
    """The one profile (current or alumni) whose name or file name matches, or a reason why not."""
    want, hits = name_key(name), []
    for folder in ("current-members", "alumni"):
        d = os.path.join(ROOT, "content", folder)
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".md"):
                text = open(os.path.join(d, fn), encoding="utf-8").read()
                if want and want in (name_key(bib.header_value(text, "name") or ""), name_key(fn[:-3])):
                    hits.append(f"content/{folder}/{fn}")
    if len(hits) == 1:
        return hits[0], None
    if hits:
        return None, f"more than one profile matches \"{name}\": {', '.join(hits)}"
    return None, (f"no profile on the website is called \"{name}\"; use your name exactly as it appears "
                  "on the People page")


def add_papers(name, dois_text, dry_run, no_render, report_path=None, replace_preprints=False):
    E, notes = bib.load(), []
    entry = {"kind": "papers", "status": "ok", "problem": "", "notes": notes, "changes": [], "name": name}
    report = [entry]
    path, problem = find_profile(name)
    typed = [d for d in (bib.find_doi(x) for x in split_lines(dois_text, r"[\s,;]+")) if d]
    unreadable = [x for x in split_lines(dois_text, r"[\s,;]+") if not bib.find_doi(x)]
    if unreadable:
        notes.append(f"not a DOI or arXiv ID, ignored: {', '.join(unreadable)}")
    if problem or not typed:
        entry.update(status="skipped", problem=problem or "no DOIs or arXiv IDs to add")
        print(f"   skipped: {entry['problem']}")
        return finish(report, report_path, True, no_render, [], 0, E)
    text = open(os.path.join(ROOT, path), encoding="utf-8").read()
    have = [d.lower() for d in bib.header_list(text, "publications") or []]
    good, added = checked_dois([d for d in typed if d not in have], E, notes)
    already = [d for d in typed if d in have]
    if already:
        notes.append(f"already on the profile: {', '.join(already)}")
    pairs = [(j, p) for j in good for p in bib.preprints_of(j) if p in E] if replace_preprints else []
    gone, relinked = preprint_choices(E, good, pairs, [], entry,
                                      "To show only the published paper, run this again with --replace-preprints.")
    entry.update(slug=os.path.basename(path)[:-3], name=bib.header_value(text, "name") or name, path=path,
                 role=bib.header_value(text, "role") or "", publications=len(have) + len(good),
                 github=link_value(text, "github"), photo="",
                 papers=[{"doi": d, "title": bib.plain(E[d].get("title", ""))} for d in good])
    if not good:
        entry.update(status="skipped", problem="none of these papers can be added (see the notes)")
        return finish(report, report_path, True, no_render, [], 0, E)
    entry["changes"] = [f"{len(good)} paper{'s' * (len(good) != 1)} added"] + entry["changes"]
    print(f"   {entry['name']}: {', '.join(entry['changes'])} -> {path}")
    if not dry_run:
        bib.set_list(os.path.join(ROOT, path), "publications", [d for d in have + good if d not in gone])
    finish(report, report_path, dry_run, no_render, [] if dry_run else [entry["slug"]], added, E, relinked)


# --- main ------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Add new lab members from intake form responses.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--zip", nargs="+", metavar="FILE", help="profile .zip file(s) saved by intake/profile-form.html")
    src.add_argument("--csv", help="the responses exported from a Google or Microsoft form")
    src.add_argument("--add-papers", metavar="NAME", help="add the papers in --dois to this person's profile")
    ap.add_argument("--photos", default=DEFAULT_PHOTOS, help="folder of downloaded headshots")
    ap.add_argument("--only", help="add just this person (part of their name)")
    ap.add_argument("--photo", help="this person's headshot (use with --only)")
    ap.add_argument("--dry-run", action="store_true", help="check and preview; write nothing")
    ap.add_argument("--no-render", action="store_true", help="don't redraw publication lists afterwards")
    ap.add_argument("--dois", default="", help="with --add-papers: DOIs or arXiv IDs, separated by spaces or lines")
    ap.add_argument("--replace-preprints", action="store_true",
                    help="with --add-papers: a paper whose DOI record names a preprint on the site replaces it")
    ap.add_argument("--expect", choices=["new", "update"], help="with --zip: refuse other kinds of .zip")
    ap.add_argument("--report", metavar="FILE", help="with --zip or --add-papers: also write what was found as JSON")
    args = ap.parse_args()
    if args.zip:
        return add_from_zips(args.zip, args.dry_run, args.no_render, args.report, args.expect)
    if args.add_papers:
        return add_papers(args.add_papers, args.dois, args.dry_run, args.no_render, args.report,
                          args.replace_preprints)

    if os.path.basename(args.csv).lower().startswith("example") and not args.dry_run:
        sys.exit("That's the example file -- try it with --dry-run.")
    with open(args.csv, encoding="utf-8-sig", newline="") as fh:     # utf-8-sig: Excel's BOM
        reader = csv.DictReader(fh)
        col = columns(reader.fieldnames or [])
        rows = list(reader)
    rows = [r for r in rows if (r.get(col["name"]) or "").strip()]
    if args.only:
        rows = [r for r in rows if norm(args.only) in norm(r[col["name"]])]
        if not rows:
            sys.exit(f"No response with a name containing '{args.only}'.")
    if args.photo and len(rows) != 1:
        sys.exit("--photo needs exactly one person: add --only \"Their Name\".")

    get = lambda r, f: (r.get(col[f]) or "").strip() if f in col else ""
    E, existing = bib.load(), content_index()
    added_people, bib_added = [], 0

    for r in rows:
        name = get(r, "name")
        slug = slugify(name)
        print(f"\n== {name}")
        if f"{slug}.md" in existing:
            print(f"   skipped: already in content/ ({existing[f'{slug}.md'][0]}); edit that file instead")
            continue
        notes = []

        # publications
        dois = []
        oid = None
        if get(r, "orcid"):
            oid = orcid_id(get(r, "orcid"))
            if not oid:
                notes.append(f"ORCID iD '{get(r, 'orcid')}' isn't valid (check digits) -- not used")
            elif "earlier" not in col or yes(get(r, "earlier")):
                found = orcid_dois(oid)
                if found is None:
                    notes.append(f"couldn't reach ORCID for {oid} -- run again later")
                else:
                    dois += found
                    print(f"   ORCID {oid}: {len(found)} publications with DOIs")
        typed = [d for d in (bib.find_doi(t) for t in split_lines(get(r, "dois"), r"[\s,;]+")) if d]
        unreadable = [t for t in split_lines(get(r, "dois"), r"[\s,;]+") if not bib.find_doi(t)]
        if unreadable:
            notes.append(f"not a DOI or arXiv ID, ignored: {', '.join(unreadable)}")
        dois = list(dict.fromkeys(dois + typed))
        good = []
        for d in dois:
            if d in E:
                good.append(d)
                continue
            rec = bib.fetch(d)
            if rec:
                E[rec["id"]] = rec
                good.append(rec["id"])
                bib_added += 1
            else:
                notes.append(f"DOI didn't resolve, left out: {d}")
        print(f"   publications: {len(good)}" + (f" ({len(typed)} typed into the form)" if typed else ""))

        # photo
        photo_rel = ""
        src = os.path.expanduser(args.photo) if args.photo else None
        if not src:
            src, problem = find_photo(name, args.photos)
            if problem:
                notes.append(problem)
        if src:
            if not os.path.exists(src):
                notes.append(f"photo not found: {src}")
            else:
                stop, warn = check_photo(src)
                if stop:
                    notes.append(stop)
                else:
                    if warn:
                        notes.append(warn)
                    ext = IMAGE_EXT[os.path.splitext(src)[1].lower()]
                    photo_rel = f"images/people/{slug}{ext}"
                    if not args.dry_run:
                        os.makedirs(PHOTO_DIR, exist_ok=True)
                        shutil.copyfile(src, os.path.join(PHOTO_DIR, slug + ext))
                    print(f"   photo: {os.path.basename(src)} -> content/{photo_rel}")
        else:
            notes.append("no headshot found -- add one later with --only and --photo, or by hand")

        year = re.search(r"\b(19|20)\d{2}\b", get(r, "year"))
        person = {
            "name": name, "pronouns": get(r, "pronouns"), "role": get(r, "role"),
            "program": get(r, "program"),
            "years": f"{year.group(0)}-present" if year else "",
            "co_mentors": [m for m in split_lines(get(r, "co_mentors"), r",|\band\b|;") if m],
            "summary": re.sub(r"\s+", " ", get(r, "summary")), "bio": get(r, "bio"),
            "education": [tidy_degree(e) for e in split_lines(get(r, "education"))],
            "photo": photo_rel,
            "email": get(r, "email") if yes(get(r, "show_email")) else "",
            "orcid_url": f"https://orcid.org/{oid}" if oid else "",
            "scholar": url(get(r, "scholar")), "website": url(get(r, "website")),
            "github": url(get(r, "github"), "https://github.com/"),
            "publications": good,
        }
        if not year:
            notes.append("no start year given -- years_in_lab left empty")
        text = profile(person)
        path = os.path.join(PEOPLE_DIR, slug + ".md")
        if args.dry_run:
            print("   would write content/current-members/" + slug + ".md:")
            print("      " + text.replace("\n", "\n      ")[:1400].rstrip())
        else:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            added_people.append(slug)
            print(f"   wrote content/current-members/{slug}.md")
        for n in notes:
            print(f"   note: {n}")

    if args.dry_run:
        print("\nDry run: nothing was written.")
        return
    if bib_added:
        bib.save(E)
    print(f"\nadded {len(added_people)} people; {bib_added} new papers in the bibliography")
    if added_people and not args.no_render:
        print("drawing their publication lists...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "render-publications.py")],
                       check=False)


if __name__ == "__main__":
    main()
