#!/usr/bin/env python3
"""The GitHub side of adding a lab member from a "New lab member" issue.

Run by .github/workflows/new-member.yml, one step at a time:

    fetch     find the profile .zip attached to the issue and download it
    check     check it, as `add-person.py --zip --dry-run` does
    pr        open, or update, the pull request for the branch the workflow pushed
    comment   report back on the issue: the pull request, or what to fix

Everything from the issue reaches this script through environment variables
and is only ever parsed here, never placed in a shell command. The steps
share what they learn through a small JSON file in $RUNNER_TEMP.

Run outside GitHub Actions (no GITHUB_REPOSITORY), `comment` and `pr` print
what they would send instead of sending it, for trying them out.
"""
import json, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP = os.environ.get("RUNNER_TEMP") or "/tmp"
STATE = os.path.join(TEMP, "new-member-state.json")
REPORT = os.path.join(TEMP, "new-member-report.json")
ZIP = os.path.join(TEMP, "submission.zip")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
SERVER = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
REPO = os.environ.get("GITHUB_REPOSITORY", "")
ISSUE = os.environ.get("ISSUE_NUMBER", "")
BASE = os.environ.get("BASE_BRANCH", "main")
BRANCH = f"new-member/issue-{ISSUE}"
LABEL = "new-member"
MARKER = "<!-- new-member-bot -->"       # finds this workflow's own comment again
MAX_BYTES = 20_000_000
# An attachment dragged into an issue: user-attachments/files/<id>/<name>.zip,
# or the older <owner>/<repo>/files/<id>/<name>.zip
ATTACHMENT = re.compile(r"https://github\.com/(?:user-attachments/files/\d+|[\w.-]+/[\w.-]+/files/\d+)"
                        r"/[^\s)\]\"'<>]+?\.zip", re.I)


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
                 "User-Agent": "kortemmelab-new-member"})
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


def download(url, token):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}",
                                               "Accept": "application/octet-stream",
                                               "User-Agent": "kortemmelab-new-member"})
    opener = urllib.request.build_opener(NoAuthElsewhere)
    with opener.open(req, timeout=60) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("the .zip is over 20 MB")
    if not data.startswith(b"PK\x03\x04"):
        raise ValueError("what came back wasn't a .zip (most likely a sign-in page)")
    return data


def ensure_label():
    """Make sure the issue carries the label (best effort: it's only for sorting)."""
    try:
        api("POST", f"/repos/{REPO}/labels", {"name": LABEL, "color": "4caac9",
                                              "description": "A new lab member's profile"})
    except urllib.error.HTTPError:
        pass                                # 422: it exists already
    try:
        api("POST", f"/repos/{REPO}/issues/{ISSUE}/labels", {"labels": [LABEL]})
    except urllib.error.HTTPError:
        pass


def fetch():
    if REPO:
        ensure_label()
    urls = ATTACHMENT.findall(os.environ.get("ISSUE_BODY", ""))
    if not urls:
        remember(stage="fetch", problem="no_zip")
        return output(zip="")
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
        remember(stage="fetched", url=url, zip_name=os.path.basename(urllib.parse.urlparse(url).path))
        return output(zip=ZIP)
    remember(stage="fetch", problem="download", url=url, tried=tried)
    output(zip="")


# --- check ---------------------------------------------------------------------------------
def check():
    run = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "add-person.py"),
                          "--zip", ZIP, "--dry-run", "--report", REPORT],
                         capture_output=True, text=True)
    print(run.stdout, run.stderr)
    try:
        entry = json.load(open(REPORT, encoding="utf-8"))[0]
    except (OSError, ValueError, IndexError):
        remember(stage="check", problem="crashed")
        return output(ok="false")
    remember(stage="checked", report=entry)
    output(ok="true" if entry["status"] == "ok" else "false")


# --- the pull request ------------------------------------------------------------------------
def pr_body(e):
    photo = (f"\n\n<img src=\"{SERVER}/{REPO}/blob/{BRANCH}/content/images/people/{e['photo']}?raw=true\" "
             f"width=\"180\" alt=\"{e['name']}'s headshot\">") if e.get("photo") else ""
    notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
    return (f"Adds **{e['name']}** ({e.get('role') or 'no role given'}) to the website, from their "
            f"profile form in #{ISSUE}.{photo}\n\n"
            f"- Profile: `content/current-members/{e['slug']}.md`\n"
            f"- Publications listed: {e.get('publications', 0)}\n"
            + (f"\n**Worth a look:**{notes}\n" if notes else "") +
            "\n**To publish:** check the profile and photo under *Files changed*, then merge. "
            "The website rebuilds by itself (`.github/workflows/build-site.yml`). "
            "To ask for changes, comment on the issue; when they attach a new .zip there, "
            "this pull request updates itself.\n\n"
            f"Closes #{ISSUE}\n\n{MARKER}")


def pr():
    e = state().get("report", {})
    title, body = f"Add {e.get('name', 'a new lab member')} to the website", pr_body(e)
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
FIX = ("Fix it in the profile form, save again, then **edit this issue** and drag the new .zip into "
       "the *Your profile .zip* box. This check runs again by itself.")


def message():
    s, run = state(), f"{SERVER}/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"
    e, stage = s.get("report", {}), s.get("stage")
    if stage == "pr" and s.get("pr_url"):
        notes = "".join(f"\n- {n}" for n in e.get("notes") or [])
        return (f"Thanks, {e.get('name', '')}! Your profile passed its checks, and pull request "
                f"#{s['pr_number']} adds it to the website. A website manager will look it over and "
                "publish it." + (f"\n\nA few things they may want to check:{notes}" if notes else "") +
                "\n\nTo change anything before then, save a new .zip from the profile form and attach "
                "it by editing this issue; the pull request updates by itself.")
    if stage == "fetch" and s.get("problem") == "no_zip":
        return ("I couldn't find a profile .zip in this issue. **Edit this issue** and drag your "
                "`…-profile.zip` (from the profile form) into the *Your profile .zip* box. Once it's "
                "there, this check runs again by itself.")
    if stage == "fetch" and s.get("problem") == "download":
        return ("I found your .zip but couldn't download it, so nothing has happened yet. This is a "
                "setting on the website's side, not something you did.\n\n"
                "**For the website manager:** GitHub didn't let this workflow read the issue's attachment "
                f"({'; '.join(s.get('tried') or ['no token'])}). Add a fine-grained personal access token "
                "with read access to this repository's contents as the repository secret `INTAKE_TOKEN` "
                "(Settings > Secrets and variables > Actions), then re-run this workflow: "
                f"{run}")
    if stage == "checked" and e.get("status") != "ok":
        return f"Your .zip couldn't be used: **{e.get('problem')}**\n\n{FIX}"
    if stage == "pr" and s.get("problem") == "not_allowed":
        return ("Your profile passed its checks, but the pull request couldn't be opened yet: this is a "
                "setting on the website's side.\n\n**For the website manager:** in Settings > Actions > "
                "General, under *Workflow permissions*, tick *Allow GitHub Actions to create and approve "
                f"pull requests*, then re-run this workflow: {run}")
    return ("Something went wrong while adding your profile, and a website manager will take a look. "
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
    steps = {"fetch": fetch, "check": check, "pr": pr, "comment": comment}
    if len(sys.argv) != 2 or sys.argv[1] not in steps:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} {'|'.join(steps)}")
    steps[sys.argv[1]]()
