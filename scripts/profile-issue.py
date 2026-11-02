#!/usr/bin/env python3
"""The GitHub side of profile submissions: "New lab member", "Update my profile" and "Add papers" issues.

Run by .github/workflows/profile-submission.yml, one step at a time:

    fetch     read the issue: find its profile .zip and download it, or (for
              Add papers) the name and DOIs typed into it
    check     check the submission, as add-person.py --dry-run does
    apply     make the change for real, on the branch the workflow has checked out
    pr        open, or update, the pull request for that branch
    comment   report back on the issue: the pull request, or what to fix

There are three kinds of submission, one per issue form, all reviewed the same way:
  - new: a .zip from the profile form, on a New lab member issue
  - update: a .zip from the form's "Update my profile" mode, on an Update my
    profile issue, merged into the existing profile (which moves to Lab
    Alumni if it gives an end year)
  - papers: a name and some DOIs typed into an Add papers issue

Everything from the issue reaches this script through environment variables
and is only ever parsed here, never placed in a shell command. The steps
share what they learn through a small JSON file in $RUNNER_TEMP.

Run outside GitHub Actions (no GITHUB_REPOSITORY), `comment` and `pr` print
what they would send instead of sending it, for trying them out.
"""
import json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.environ.get("RUNNER_TEMP") or "/tmp"
STATE = os.path.join(TEMP, "profile-submission-state.json")
REPORT = os.path.join(TEMP, "profile-submission-report.json")
ZIP = os.path.join(TEMP, "submission.zip")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
ISSUE = os.environ.get("ISSUE_NUMBER", "")
AUTHOR = os.environ.get("ISSUE_AUTHOR", "")
KIND = os.environ.get("SUBMISSION_KIND") if os.environ.get("SUBMISSION_KIND") in ("update", "papers") else "new"
BASE = os.environ.get("BASE_BRANCH", "main")
BRANCH = f"profile/issue-{ISSUE}"
LABELS = {"new": ("new-member", "A new lab member's profile"),
          "update": ("profile-update", "A change to a lab member's profile"),
          "papers": ("add-papers", "New papers for a lab member's profile")}
MARKER = "<!-- profile-submission-bot -->"       # finds this workflow's own comment again
MAX_BYTES = 20_000_000
# An attachment dragged into an issue: user-attachments/files/<id>/<name>.zip,
# or the older <owner>/<repo>/files/<id>/<name>.zip
ATTACHMENT = re.compile(r"https://github\.com/(?:user-attachments/files/\d+|[\w.-]+/[\w.-]+/files/\d+)"
                        r"/[^\s)\]\"'<>]+?\.zip", re.I)
# The issue forms' field labels (.github/ISSUE_TEMPLATE/*.yml), which head each answer
NAME_FIELD = "Your name as it appears on the website"
DOIS_FIELD = "Papers to add (DOIs)"


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
                 "User-Agent": "kortemmelab-profile-submission"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read()
        return json.loads(data) if data else None


def api_error(e):
    try:
        return json.loads(e.read()).get("message", "")
    except Exception:
        return str(e)


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


# --- fetch -------------------------------------------------------------------------------
class NoAuthElsewhere(urllib.request.HTTPRedirectHandler):
    """Attachments redirect to a signed storage URL, which rejects a second credential."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and urllib.parse.urlparse(newurl).hostname != urllib.parse.urlparse(req.full_url).hostname:
            new.remove_header("Authorization")
        return new


def download(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/octet-stream",
                                               "User-Agent": "kortemmelab-profile-submission"})
    opener = urllib.request.build_opener(NoAuthElsewhere)
    with opener.open(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("the .zip is over 20 MB")
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("what came back wasn't a .zip (most likely a sign-in page)")
    return data


def ensure_label():
    """Make sure the issue carries its label (best effort: it's only for sorting)."""
    name, description = LABELS[KIND]
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
    if KIND == "papers":
        name, dois = answers.get(NAME_FIELD, ""), answers.get(DOIS_FIELD, "")
        if name and dois:
            remember(stage="fetched", lane="papers", name=name, dois=dois)
            return output(lane="papers")
        remember(stage="fetch", problem="papers_missing")
        return output(lane="")
    urls = ATTACHMENT.findall(body)
    if not urls:
        remember(stage="fetch", problem="no_zip")
        return output(lane="")
    url, tried = urls[-1], []                # the newest attachment, if there are several
    for name in ("GH_TOKEN", "INTAKE_TOKEN"):
        token = os.environ.get(name)
        if not token:
            continue
        try:
            data = download(url, token)
        except (urllib.error.URLError, ValueError, OSError) as e:
            tried.append(f"{name}: {getattr(e, 'code', '') or e}")
            continue
        with open(ZIP, "wb") as fh:
            fh.write(data)
        remember(stage="fetched", lane="zip", url=url)
        return output(lane="zip")
    remember(stage="fetch", problem="download", url=url, tried=tried)
    output(lane="")


# --- check and apply -------------------------------------------------------------------------
def add_person(dry_run):
    s = state()
    cmd = [sys.executable, os.path.join(ROOT, "scripts", "add-person.py"), "--report", REPORT]
    if s.get("lane") == "papers":
        cmd += ["--add-papers", s["name"], "--dois", s["dois"]]
    else:
        cmd += ["--zip", ZIP, "--expect", KIND]
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
    name = e.get("name") or "a lab member"
    return {"new": f"Add {name} to the website", "update": f"Update {name}'s profile",
            "papers": f"Add papers to {name}'s profile"}[e.get("kind", "new")]


def pr_body(e):
    kind = e.get("kind", "new")
    photo = (f"\n\n<img src=\"{SERVER}/{REPO}/blob/{BRANCH}/content/images/people/{e['photo']}?raw=true\" "
             f"width=\"180\" alt=\"{e['name']}'s headshot\">") if e.get("photo") else ""
    what = {"new": f"Adds **{e['name']}** ({e.get('role') or 'no role given'}) to the website",
            "update": f"Updates **{e['name']}**'s profile", "papers": f"Adds papers to **{e['name']}**'s profile"}[kind]
    changes = "".join(f"\n- {c}" for c in e.get("changes") or [])
    papers = "".join(f"\n- {p['title'] or p['doi']} (`{p['doi']}`)" for p in e.get("papers") or [])
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
            + (f"\n**Papers added:**{papers}\n" if papers else "")
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
    fix = ("Fix it in the profile form, save again, then **edit this issue** and drag the new .zip into its box."
           if s.get("lane") != "papers" else "**Edit this issue** to correct it.") + \
          " This check runs again by itself."
    if stage == "pr" and s.get("pr_url"):
        notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
        done = {"new": "Your profile passed its checks, and", "update": "Your changes passed their checks, and",
                "papers": "Your papers were found, and"}[e.get("kind", "new")]
        return (f"Thanks, {e.get('name', '')}! {done} pull request #{s['pr_number']} makes the change: "
                f"{', '.join(e.get('changes') or [])}. A website manager will look it over and publish it."
                + (f"\n\nA few things they may want to check:{notes}" if notes else "") +
                "\n\nTo change anything before then, edit this issue ("
                + ("different DOIs" if e.get("kind") == "papers" else "attach a new .zip")
                + "); the pull request updates by itself.")
    if stage == "fetch" and s.get("problem") == "no_zip":
        box, file = (("Your updated profile .zip", "…-profile-update.zip") if KIND == "update"
                     else ("Your profile .zip", "…-profile.zip"))
        return ("I couldn't find a profile .zip in this issue. **Edit this issue** and drag your "
                f"`{file}` (from the profile form) into the *{box}* box. Once it's there, this check "
                "runs again by itself.")
    if stage == "fetch" and s.get("problem") == "papers_missing":
        return ("I need both your name, as it appears on the website, and at least one DOI. **Edit this "
                "issue** to fill them in, and this check runs again by itself.")
    if stage == "fetch" and s.get("problem") == "download":
        return ("I found your .zip but couldn't download it, so nothing has happened yet. This is a "
                "setting on the website's side, not something you did.\n\n"
                "**For the website manager:** GitHub didn't let this workflow read the issue's attachment "
                f"({'; '.join(s.get('tried') or ['no token'])}). Add a fine-grained personal access token "
                "with read access to this repository's contents as the repository secret `INTAKE_TOKEN` "
                "(Settings > Secrets and variables > Actions), then re-run this workflow: "
                f"{run}")
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
    body = f"{message()}\n\n{MARKER}"
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
