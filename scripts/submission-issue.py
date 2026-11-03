#!/usr/bin/env python3
"""The GitHub side of submissions made through the website's issue forms.

Run by .github/workflows/submission.yml, one step at a time:

    fetch     read the issue: download its profile .zip or photos, or read its news
    check     check the submission, as add-person.py / add-content.py --dry-run do
    apply     make the change for real, on the branch the workflow has checked out
    pr        open, or update, the pull request for that branch
    comment   report back on the issue: the pull request, or what to fix

There are four kinds, one per issue form (.github/ISSUE_TEMPLATE/), all
reviewed the same way:
  - new: a .zip from the profile form, on a New lab member issue
  - update: a .zip from the form's "Update my profile" mode, merged into the
    existing profile (which moves to Lab Alumni if it gives an end year)
  - news: a month, year and sentence, on an Add news issue
  - gallery: photos and a caption, on an Add photos to the gallery issue; the
    photos are scaled down and their metadata (GPS location) removed

Everything from the issue reaches this script through environment variables
and is only ever parsed here, never placed in a shell command. The steps
share what they learn through a small JSON file in $RUNNER_TEMP.

Run outside GitHub Actions (no GITHUB_REPOSITORY), `comment` and `pr` print
what they would send instead of sending it, for trying them out.
"""
import datetime, json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.environ.get("RUNNER_TEMP") or "/tmp"
STATE = os.path.join(TEMP, "submission-state.json")
REPORT = os.path.join(TEMP, "submission-report.json")
ZIP = os.path.join(TEMP, "submission.zip")
PHOTOS = os.path.join(TEMP, "photos")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
ISSUE = os.environ.get("ISSUE_NUMBER", "")
AUTHOR = os.environ.get("ISSUE_AUTHOR", "")
BASE = os.environ.get("BASE_BRANCH", "main")
BRANCH = f"submission/issue-{ISSUE}"
# Each kind: its label (set by its issue form), the title its form starts with, and a description
KINDS = {"new": ("new-member", "New lab member", "A new lab member's profile"),
         "update": ("profile-update", "Profile update", "A change to a lab member's profile"),
         "news": ("news", "News:", "Lab news for the website"),
         "gallery": ("gallery", "Gallery:", "Photos for the website's gallery")}


def issue_kind():
    try:
        labels = set(json.loads(os.environ.get("ISSUE_LABELS") or "[]"))
    except ValueError:
        labels = set()
    title = os.environ.get("ISSUE_TITLE", "")
    for kind, (label, prefix, _) in KINDS.items():
        if label in labels:
            return kind
    for kind, (label, prefix, _) in KINDS.items():
        if title.startswith(prefix):
            return kind
    return os.environ.get("SUBMISSION_KIND") if os.environ.get("SUBMISSION_KIND") in KINDS else "new"


KIND = issue_kind()
MARKER = "<!-- submission-bot -->"               # finds this workflow's own comment again
MAX_BYTES = 20_000_000
MAX_PHOTOS = 10
# An attachment dragged into an issue: user-attachments/files/<id>/<name>.zip,
# or the older <owner>/<repo>/files/<id>/<name>.zip
ATTACHMENT = re.compile(r"https://github\.com/(?:user-attachments/files/\d+|[\w.-]+/[\w.-]+/files/\d+)"
                        r"/[^\s)\]\"'<>]+?\.zip", re.I)
# An image dragged into an issue: user-attachments/assets/<uuid>, or the older forms
IMAGE = re.compile(r"https://(?:github\.com/user-attachments/assets/[0-9a-f-]{36}"
                   r"|github\.com/[\w.-]+/[\w.-]+/assets/\d+/[0-9a-f-]{36}"
                   r"|user-images\.githubusercontent\.com/\d+/[^\s)\]\"'<>]+?\.(?:png|jpe?g))", re.I)
# The issue forms' field labels, which head each answer in the issue's text
FIELDS = {"month": "Month", "year": "Year", "news": "News", "link": "Link (optional)",
          "photos": "Photos", "caption": "Caption (optional)"}
MAGIC = {"zip": (b"PK\x03\x04",), "image": (b"\xff\xd8", b"\x89PNG", b"RIFF")}


# --- shared state, outputs, the GitHub API -------------------------------------------
def state():
    try:
        return json.load(open(STATE, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def remember(**kw):
    s = state()
    s.update(kw)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2, ensure_ascii=False)


def output(**kw):
    """Step outputs, read by later steps' `if:` conditions."""
    path = os.environ.get("GITHUB_OUTPUT")
    lines = "".join(f"{k}={v}\n" for k, v in kw.items())
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(lines)
    else:
        print(lines, end="")


def api(method, path, body=None):
    req = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "kortemmelab-submission"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        return json.loads(data) if data else None


def api_error(e):
    try:
        return json.loads(e.read()).get("message", "")
    except Exception:
        return str(e)


# --- fetch -------------------------------------------------------------------------------
class NoAuthElsewhere(urllib.request.HTTPRedirectHandler):
    """Attachments redirect to a signed storage URL, which rejects a second credential."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlparse(newurl).hostname != urllib.parse.urlparse(req.full_url).hostname:
            new.remove_header("Authorization")
        return new


def download(url, token, what="zip"):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/octet-stream",
                                               "User-Agent": "kortemmelab-submission"})
    opener = urllib.request.build_opener(NoAuthElsewhere)
    with opener.open(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"the {'.zip' if what == 'zip' else 'photo'} is over 20 MB")
    if not data.startswith(MAGIC[what]):
        raise ValueError(f"what came back wasn't a {'.zip' if what == 'zip' else 'JPG or PNG'} "
                         "(most likely a sign-in page)")
    return data


def fetch_file(url, what):
    """The file at an attachment URL, trying the workflow's token, then INTAKE_TOKEN."""
    tried = []
    for name in ("GH_TOKEN", "INTAKE_TOKEN"):
        token = os.environ.get(name)
        if not token:
            print(f"{name}: not set")              # INTAKE_TOKEN: no repository secret by that name
            tried.append(f"{name}: not set")
            continue
        try:
            data = download(url, token, what)
        except (urllib.error.URLError, ValueError, OSError) as e:
            print(f"{name}: refused ({getattr(e, 'code', '') or e})")
            tried.append(f"{name}: {getattr(e, 'code', '') or e}")
            continue
        print(f"{name}: downloaded {len(data)} bytes")
        return data, tried
    return None, tried


def fields(body):
    """An issue form's answers, by field label ("_No response_" counts as empty)."""
    out, label = {}, None
    for ln in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", ln)
        if m:
            label = m.group(1)
            out[label] = []
        elif label:
            out[label].append(ln)
    return {k: ("" if "\n".join(v).strip() == "_No response_" else "\n".join(v).strip()) for k, v in out.items()}


def ensure_label():
    """Make sure the issue carries its label (best effort: it's only for sorting)."""
    name, _, description = KINDS[KIND]
    try:
        api("POST", f"/repos/{REPO}/labels", {"name": name, "color": "4caac9", "description": description})
    except urllib.error.HTTPError:
        pass                                # 422: it exists already
    try:
        api("POST", f"/repos/{REPO}/issues/{ISSUE}/labels", {"labels": [name]})
    except urllib.error.HTTPError:
        pass


def fetch():
    if REPO:
        ensure_label()
    body = os.environ.get("ISSUE_BODY", "")
    answers = fields(body)
    remember(kind=KIND)
    print(f"kind: {KIND}")
    if KIND == "news":
        news = {k: answers.get(FIELDS[k], "") for k in ("month", "year", "news", "link")}
        if not (news["month"] and news["year"] and news["news"]):
            remember(stage="fetch", problem="news_missing")
            return output(lane="")
        remember(stage="fetched", lane="news", news=news)
        return output(lane="news")
    if KIND == "gallery":
        urls = list(dict.fromkeys(IMAGE.findall(answers.get(FIELDS["photos"], "") or body)))
        if not urls:
            remember(stage="fetch", problem="no_photos")
            return output(lane="")
        if len(urls) > MAX_PHOTOS:
            remember(stage="fetch", problem="too_many_photos", count=len(urls))
            return output(lane="")
        os.makedirs(PHOTOS, exist_ok=True)
        files = []
        for n, url in enumerate(urls, 1):
            print(f"photo {n}: {url}")
            data, tried = fetch_file(url, "image")
            if data is None:
                remember(stage="fetch", problem="download", url=url, tried=tried, what="photo")
                return output(lane="")
            path = os.path.join(PHOTOS, f"photo-{n}")
            with open(path, "wb") as fh:
                fh.write(data)
            files.append(path)
        remember(stage="fetched", lane="gallery", photos=files, caption=answers.get(FIELDS["caption"], ""))
        return output(lane="gallery")
    urls = ATTACHMENT.findall(body)
    if not urls:
        remember(stage="fetch", problem="no_zip")
        return output(lane="")
    url = urls[-1]                           # the newest attachment, if there are several
    print(f"attachment: {url}")
    data, tried = fetch_file(url, "zip")
    if data is None:
        remember(stage="fetch", problem="download", url=url, tried=tried, what=".zip")
        return output(lane="")
    with open(ZIP, "wb") as fh:
        fh.write(data)
    remember(stage="fetched", lane="zip", url=url)
    output(lane="zip")


# --- check and apply -------------------------------------------------------------------------
def add_person(dry_run):
    """Run the script that makes this kind of change; its report says what it found."""
    s, scripts = state(), os.path.join(ROOT, "scripts")
    if s.get("lane") == "news":
        n = s["news"]
        cmd = [sys.executable, os.path.join(scripts, "add-content.py"), "news", "--month", n["month"],
               "--year", n["year"], "--text", n["news"], "--link", n["link"]]
    elif s.get("lane") == "gallery":
        cmd = [sys.executable, os.path.join(scripts, "add-content.py"), "photos",
               "--caption", s.get("caption", "")] + s["photos"]
    else:
        cmd = [sys.executable, os.path.join(scripts, "add-person.py"), "--zip", ZIP, "--expect", KIND]
    cmd += ["--report", REPORT]
    run = subprocess.run(cmd + (["--dry-run"] if dry_run else []), capture_output=True, text=True)
    print(run.stdout, run.stderr)
    try:
        return json.load(open(REPORT, encoding="utf-8"))[0]
    except (OSError, ValueError, IndexError):
        return None


def identity(entry):
    """Whether the GitHub account that opened the issue is the one on the profile."""
    link = (entry.get("github") or "").rstrip("/")
    login = re.sub(r"^https?://(www\.)?github\.com/", "", link, flags=re.I).split("/")[0]
    if not link or not login:
        return "none"
    return "match" if AUTHOR and login.lower() == AUTHOR.lower() else "mismatch"


def check():
    entry = add_person(dry_run=True)
    if entry is None:
        remember(stage="check", problem="crashed")
        return output(ok="false")
    entry["identity"] = identity(entry)
    remember(stage="checked", report=entry)
    output(ok="true" if entry["status"] == "ok" else "false")


def apply():
    entry = add_person(dry_run=False)
    if entry is None or entry["status"] != "ok":
        remember(stage="apply", problem="crashed")
        sys.exit("the change couldn't be applied; see the output above")


# --- the pull request ------------------------------------------------------------------------
def pr_title(e):
    kind, name = e.get("kind", "new"), e.get("name") or "a lab member"
    if kind == "news":
        text = e.get("text", "")
        return f"News: {text if len(text) <= 70 else text[:67].rstrip() + '…'}"
    if kind == "gallery":
        n = len(e.get("photos") or [])
        return f"Gallery: {n} photo{'s' * (n != 1)}" + (f", “{e['caption']}”" if e.get("caption") else "")
    return {"new": f"Add {name} to the website", "update": f"Update {name}'s profile"}[kind]


def content_pr_body(e):
    """News or gallery: what will appear, and where."""
    notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
    if e["kind"] == "news":
        what = (f"Adds a news item for **{e.get('date')}** to the News page, from #{ISSUE}:\n\n"
                f"> {e.get('text')}" + (f"\n>\n> Links to {e['link']}" if e.get("link") else "")
                + f"\n\nIt goes in date order in `content/news.md`.")
    else:
        pics = "".join(f"\n<img src=\"{SERVER}/{REPO}/blob/{BRANCH}/{p['file']}?raw=true\" width=\"220\" "
                       f"alt=\"Photo {k}\"> " for k, p in enumerate(e.get("photos") or [], 1))
        sizes = "".join(f"\n- `{p['file']}`: {p['saved']} pixels (from {p['original']})" for p in e.get("photos") or [])
        what = (f"Adds {len(e.get('photos') or [])} photo(s) to the top of the gallery, from #{ISSUE}"
                + (f", captioned “{e['caption']}” (on the first photo)" if e.get("caption") else ", with no caption")
                + f".\n{pics}\n\nEach was turned upright, scaled down, and saved **without its metadata**, "
                "so the camera's GPS location isn't published:" + sizes)
    return (what + (f"\n\n**Worth a look:**{notes}" if notes else "")
            + f"\n\nSubmitted by `{AUTHOR}`, who confirmed on the issue "
            + ("that everyone pictured is happy for the photos to be online." if e["kind"] == "gallery" else "that it can be published.")
            + "\n\n**To publish:** check it under *Files changed*, then merge. The website rebuilds by itself. "
            "To ask for changes, comment on the issue; when they edit it, this pull request updates itself."
            f"\n\nCloses #{ISSUE}\n\n{MARKER}")


def pr_body(e):
    kind = e.get("kind", "new")
    if kind in ("news", "gallery"):
        return content_pr_body(e)
    photo = (f"\n\n<img src=\"{SERVER}/{REPO}/blob/{BRANCH}/content/images/people/{e['photo']}?raw=true\" "
             f"width=\"180\" alt=\"{e['name']}'s headshot\">") if e.get("photo") else ""
    what = {"new": f"Adds **{e['name']}** ({e.get('role') or 'no role given'}) to the website",
            "update": f"Updates **{e['name']}**'s profile"}[kind]
    changes = "".join(f"\n- {c}" for c in e.get("changes") or [])
    replaced = "".join(f"\n- the preprint \"{r['title']}\" (`{r['preprint']}`) by `{r['published']}`"
                       for r in e.get("replaces") or [])
    notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
    who = {"match": f"✓ Opened by `{AUTHOR}`, the GitHub account on this profile.",
           "mismatch": f"⚠ Opened by `{AUTHOR}`, but this profile's GitHub link is {e.get('github')}. "
                       "Check it's really them, or someone they asked, before merging.",
           "none": f"Opened by `{AUTHOR}`. This profile has no GitHub link to compare with"
                   + (", so check the change is really theirs before merging." if kind != "new" else ".")
           }[e.get("identity", "none")]
    return (f"{what}, from #{ISSUE}.{photo}\n\n"
            f"- File: `{e.get('path')}`\n- Publications listed: {e.get('publications', 0)}\n"
            + (f"\n**What changes:**{changes}\n" if changes and kind != "new" else "")
            + (f"\n**Preprints replaced** (confirmed by the member; gone from every page once this is merged):"
               f"{replaced}\n" if replaced else "")
            + (f"\n**Worth a look:**{notes}\n" if notes else "")
            + f"\n{who}\n\n"
            "**To publish:** check the changes under *Files changed*, then merge. The website rebuilds by "
            "itself (`.github/workflows/build-site.yml`). To ask for changes, comment on the issue; when they "
            "edit it with a new submission, this pull request updates itself.\n\n"
            f"Closes #{ISSUE}\n\n{MARKER}")


def pr():
    e = state().get("report", {})
    title, body = pr_title(e), pr_body(e)
    if not REPO:
        print(f"would open a pull request from {BRANCH}:\n{title}\n\n{body}")
        return
    owner = REPO.split("/")[0]
    try:
        found = api("GET", f"/repos/{REPO}/pulls?state=open&head={urllib.parse.quote(owner + ':' + BRANCH)}")
        if found:
            p = api("PATCH", f"/repos/{REPO}/pulls/{found[0]['number']}", {"title": title, "body": body})
        else:
            p = api("POST", f"/repos/{REPO}/pulls", {"title": title, "body": body, "head": BRANCH, "base": BASE})
    except urllib.error.HTTPError as err:
        msg = api_error(err)
        remember(stage="pr", problem="not_allowed" if "not permitted" in msg.lower() else "failed", detail=msg)
        return output(pr="")
    remember(stage="pr", pr_url=p["html_url"], pr_number=p["number"])
    output(pr=p["html_url"])


# --- the comment on the issue ------------------------------------------------------------------
def message():
    s, run = state(), f"{SERVER}/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    e, stage = s.get("report", {}), s.get("stage")
    fix = {"news": "**Edit this issue** to correct it.",
           "gallery": "**Edit this issue** to change the photos or caption."}.get(
        KIND, "Fix it in the profile form, save again, then **edit this issue** and drag the new .zip into its box.") \
        + " This check runs again by itself."
    if stage == "pr" and s.get("pr_url"):
        notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
        kind = e.get("kind", "new")
        if kind in ("news", "gallery"):
            return (f"Thanks! Pull request #{s['pr_number']} adds "
                    + ("your news item to the News page" if kind == "news" else
                       f"{len(e.get('photos') or [])} photo(s) to the gallery, scaled down and with their location data removed")
                    + ". A website manager will look it over and publish it."
                    + (f"\n\nA few things they may want to check:{notes}" if notes else "")
                    + "\n\nTo change anything before then, edit this issue; the pull request updates by itself.")
        done = {"new": "Your profile passed its checks, and",
                "update": "Your changes passed their checks, and"}[kind]
        return (f"Thanks, {e.get('name', '')}! {done} pull request #{s['pr_number']} makes the change: "
                f"{', '.join(e.get('changes') or [])}. A website manager will look it over and publish it."
                + (f"\n\nA few things they may want to check:{notes}" if notes else "") +
                "\n\nTo change anything before then, save a new .zip from the profile form and attach it "
                "by editing this issue; the pull request updates by itself.")
    if stage == "fetch" and s.get("problem") == "news_missing":
        return ("I need the month, the year and the news itself. **Edit this issue** to fill them in, "
                "and this check runs again by itself.")
    if stage == "fetch" and s.get("problem") == "no_photos":
        return ("I couldn't find any photos in this issue. **Edit this issue** and drag your photos (JPG or "
                "PNG) into the *Photos* box. Once they're there, this check runs again by itself.")
    if stage == "fetch" and s.get("problem") == "too_many_photos":
        return (f"That's {s.get('count')} photos; please send at most {MAX_PHOTOS} per issue. **Edit this "
                "issue** to remove some (open another issue for the rest).")
    if stage == "fetch" and s.get("problem") == "no_zip":
        box, file = (("Your updated profile .zip", "…-profile-update.zip") if KIND == "update"
                     else ("Your profile .zip", "…-profile.zip"))
        return ("I couldn't find a profile .zip in this issue. **Edit this issue** and drag your "
                f"`{file}` (from the profile form) into the *{box}* box. Once it's there, this check "
                "runs again by itself.")
    if stage == "fetch" and s.get("problem") == "download":
        return (f"I found your {s.get('what', '.zip')} but couldn't download it, so nothing has happened yet. This is a "
                "setting on the website's side, not something you did.\n\n"
                "**For the website manager:** GitHub didn't let this workflow read the issue's attachment "
                f"({'; '.join(s.get('tried') or ['no token'])}). "
                + ("A token saved as `INTAKE_TOKEN` was refused too, so GitHub doesn't let tokens read "
                   "attachments in this repository; see `intake/github-issue-route.md`."
                   if any(x.startswith("INTAKE_TOKEN:") and "not set" not in x for x in s.get("tried") or [])
                   else "Add a fine-grained personal access token with read access to this repository's "
                        "contents as the repository secret `INTAKE_TOKEN` (Settings > Secrets and variables > "
                        "Actions > Repository secrets), then edit this issue (any small change) to check again.")
                + f" Run: {run}")
    if stage == "checked" and e.get("status") != "ok":
        notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
        return (f"That couldn't be used: **{e.get('problem')}**" + (f"\n{notes}" if notes else "")
                + f"\n\n{fix}")
    if stage == "pr" and s.get("problem") == "not_allowed":
        return ("Your submission passed its checks, but the pull request couldn't be opened yet: this is a "
                "setting on the website's side.\n\n**For the website manager:** in Settings > Actions > "
                "General, under *Workflow permissions*, tick *Allow GitHub Actions to create and approve "
                f"pull requests*, then re-run this workflow: {run}")
    return ("Something went wrong while making the change, and a website manager will take a look. "
            f"You don't need to do anything for now.\n\n**For the website manager:** see {run}")


def comment():
    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    body = f"{message()}\n\n<sub>Checked {when}" + (f", attempt {attempt}" if attempt != "1" else "") + \
           f".</sub>\n\n{MARKER}"
    if not REPO:
        print(body)
        return
    comments = api("GET", f"/repos/{REPO}/issues/{ISSUE}/comments?per_page=100") or []
    mine = [c for c in comments if MARKER in (c.get("body") or "")]
    if mine:
        api("PATCH", f"/repos/{REPO}/issues/comments/{mine[-1]['id']}", {"body": body})
    else:
        api("POST", f"/repos/{REPO}/issues/{ISSUE}/comments", {"body": body})


if __name__ == "__main__":
    steps = {"fetch": fetch, "check": check, "apply": apply, "pr": pr, "comment": comment}
    if len(sys.argv) != 2 or sys.argv[1] not in steps:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} {'|'.join(steps)}")
    steps[sys.argv[1]]()
