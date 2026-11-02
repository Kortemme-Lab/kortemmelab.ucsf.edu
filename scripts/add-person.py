#!/usr/bin/env python3
"""Add new lab members from the intake form's responses.

    python3 scripts/add-person.py --csv intake/responses.csv
    python3 scripts/add-person.py --csv intake/responses.csv --dry-run
    python3 scripts/add-person.py --csv intake/responses.csv --only "Jane Doe" --photo ~/jane.jpg
    python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip

Two ways in. --zip takes the file saved by the new-member form
(intake/profile-form.html, also at docs/profile-form.html): the profile and
headshot are already in shape, so they're checked and filed. --csv takes the
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
ZIP_PROFILE = re.compile(r"^content/current-members/([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
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


# --- a .zip from the new-member form -----------------------------------------------------
def read_zip(path):
    """The profile text, its name, and the photo (name, bytes) in a form .zip.

    Anything else in the file, or a path outside those two places, stops it:
    the .zip came from outside the lab, so nothing in it is trusted blindly.
    """
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        return None, f"not a readable .zip ({e})"
    profile_name, photo, problems = None, None, []
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
            else:
                problems.append(f"unexpected file in the .zip: {name}")
        if not profile_name:
            problems.append("no profile (content/current-members/<name>.md) in the .zip")
        if photo and profile_name and ZIP_PHOTO.match(photo).group(1) != ZIP_PROFILE.match(profile_name).group(1):
            problems.append(f"the photo's name ({photo}) doesn't match the profile's ({profile_name})")
        if problems:
            return None, "; ".join(problems)
        text = z.read(profile_name).decode("utf-8")
        return {"slug": ZIP_PROFILE.match(profile_name).group(1), "text": text,
                "photo": (photo, z.read(photo)) if photo else None}, None


def add_from_zips(paths, dry_run, no_render):
    E, existing = bib.load(), content_index()
    added_people, bib_added = [], 0
    for path in paths:
        print(f"\n== {os.path.basename(path)}")
        got, problem = read_zip(os.path.expanduser(path))
        if problem:
            print(f"   skipped: {problem}")
            continue
        slug, text, notes = got["slug"], got["text"], []
        name = bib.header_value(text, "name")
        if not text.startswith("---\n") or not name:
            print("   skipped: the profile has no header with a name; was it made by the form?")
            continue
        print(f"   {name} -> content/current-members/{slug}.md")
        if f"{slug}.md" in existing:
            print(f"   skipped: already in content/ ({existing[f'{slug}.md'][0]}); edit that file instead,"
                  " or delete it first to replace it")
            continue

        # publications: every DOI is checked, as for --csv
        good = []
        for d in dict.fromkeys(bib.clean_doi(d) for d in (bib.header_list(text, "publications") or [])):
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
        print(f"   publications: {len(good)}")

        # photo
        photo_bytes = None
        if got["photo"]:
            zname, photo_bytes = got["photo"]
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(zname)[1]) as tmp:
                tmp.write(photo_bytes)
                tmp.flush()
                stop, warn = check_photo(tmp.name)
            if stop:
                notes.append(stop)
                photo_bytes = None
            elif warn:
                notes.append(warn)
            if photo_bytes is not None and not looks_like_image(zname, photo_bytes):
                notes.append(f"{os.path.basename(zname)} isn't a readable JPG or PNG, left out")
                photo_bytes = None
        if photo_bytes is None:
            notes.append(f"no headshot -- later, save one as content/images/people/{slug}.jpg"
                         f' and set photo: "images/people/{slug}.jpg" in their file')

        if not dry_run:
            dest = os.path.join(PEOPLE_DIR, slug + ".md")
            with open(dest, "w", encoding="utf-8") as fh:
                fh.write(text)
            bib.set_list(dest, "publications", good)
            if photo_bytes is not None:
                os.makedirs(PHOTO_DIR, exist_ok=True)
                with open(os.path.join(PHOTO_DIR, os.path.basename(got["photo"][0])), "wb") as fh:
                    fh.write(photo_bytes)
            else:
                t = open(dest, encoding="utf-8").read()
                with open(dest, "w", encoding="utf-8") as fh:
                    fh.write(re.sub(r'(?m)^photo: .*$', 'photo: ""', t, count=1))
            added_people.append(slug)
            print(f"   wrote content/current-members/{slug}.md"
                  + (f" and content/images/people/{os.path.basename(got['photo'][0])}" if photo_bytes is not None else ""))
        for n in notes:
            print(f"   note: {n}")

    if dry_run:
        print("\nDry run: nothing was written.")
        return
    if bib_added:
        bib.save(E)
    print(f"\nadded {len(added_people)} people; {bib_added} new papers in the bibliography")
    if added_people and not no_render:
        print("drawing their publication lists...")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "render-publications.py")],
                       check=False)
    if added_people:
        print("\nNext: python3 scripts/build-site.py, look at their page, then commit and push.")


def looks_like_image(name, data):
    """The photo really is the kind of image its name says (it came from outside)."""
    ext = os.path.splitext(name)[1].lower()
    magic = {".jpg": b"\xff\xd8", ".png": b"\x89PNG", ".webp": b"RIFF"}
    return data.startswith(magic.get(ext, b"\0\0\0\0"))


# --- main ------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Add new lab members from intake form responses.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--zip", nargs="+", metavar="FILE", help="profile .zip file(s) saved by intake/profile-form.html")
    src.add_argument("--csv", help="the responses exported from a Google or Microsoft form")
    ap.add_argument("--photos", default=DEFAULT_PHOTOS, help="folder of downloaded headshots")
    ap.add_argument("--only", help="add just this person (part of their name)")
    ap.add_argument("--photo", help="this person's headshot (use with --only)")
    ap.add_argument("--dry-run", action="store_true", help="check and preview; write nothing")
    ap.add_argument("--no-render", action="store_true", help="don't redraw publication lists afterwards")
    args = ap.parse_args()
    if args.zip:
        return add_from_zips(args.zip, args.dry_run, args.no_render)

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
            "education": split_lines(get(r, "education")),
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
