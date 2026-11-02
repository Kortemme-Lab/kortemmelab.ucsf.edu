# Plan: new members submit through a GitHub issue

**Status: proposed, not built.** The rest of the intake path is in place: the
form (`intake/profile-form.html`) saves a `.zip`, `add-person.py --zip` files
it, and `.github/workflows/build-site.yml` rebuilds the site on every push.
This plan adds the last step, so a manager never runs a command.

## How it would work

1. **The member** fills in the form, saves `jane-doe-profile.zip`, and opens a
   *New lab member* issue on GitHub. The issue form asks for the `.zip`
   (dragged into a box) and a tick confirming they're happy for it to be
   published. The issue is labeled `new-member` automatically.
2. **A workflow checks it** within a minute or two. It downloads the `.zip`,
   runs the same checks as `add-person.py --zip`, and comments on the issue
   with what it found: name, role, the number of papers, the photo, and
   anything to fix (a DOI that doesn't resolve, a small photo). If something's
   wrong, the member fixes it in the form, saves again, and attaches the new
   `.zip` to the issue. The workflow checks again.
3. **If the checks pass**, the same workflow opens a pull request, *Add Jane
   Doe to the website*. The pull request has their profile file, headshot,
   redrawn publication lists and the rebuilt `docs/`, and the words "Closes
   #12". On the pull request's *Files changed* tab the manager sees the
   profile text and the photo itself.
4. **The manager clicks Merge.** That's the approval. The issue closes, and the
   merge is a push to `main`, so `build-site.yml` runs and confirms the
   site is current. If Pages is on, the site updates by itself.

Nothing reaches `main` without that merge: the workflow can propose a change,
never make one.

## What gets built

| File | What it does |
|---|---|
| `.github/ISSUE_TEMPLATE/new-member.yml` | The issue form: a link to the profile form, a box for the `.zip`, the consent tick. Sets the title to "New lab member: …" and the `new-member` label. |
| `.github/ISSUE_TEMPLATE/config.yml` | Turns off blank issues, if wanted, so every issue starts from a form. |
| `.github/workflows/new-member.yml` | Runs when a `new-member` issue is opened or edited: *check* (download, validate, comment), then *propose* (branch, `add-person.py --zip`, build, pull request). |
| `scripts/add-person.py` | Gains `--report report.json`, so the workflow can write its comment from the results instead of reading console text. |

About 150 lines of new YAML and Python in total, plus testing with a few
deliberately wrong submissions.

## Security, since the `.zip` comes from outside

- **Only people with access can submit.** The repository is private, so only
  its collaborators can open issues; the workflow also checks the issue
  author's association and ignores anyone else, in case the repository is
  ever made public.
- **Issue text is never run.** It reaches the workflow's scripts only as an
  environment variable and is parsed in Python, never pasted into a shell
  command. That's the usual way GitHub workflows get attacked, and it's
  avoided entirely.
- **The `.zip` is checked before anything is written.** `add-person.py --zip`
  already refuses any file other than one profile and one matching headshot,
  any path outside those two folders, oversized files, and photos that
  aren't really JPG/PNG. Only a `https://github.com/user-attachments/…zip`
  link is downloaded, with a size cap.
- **Each job gets only the permissions it needs.** *Check* can read the
  repository and comment. *Propose* can push a branch and open a pull request,
  but can't push to `main`. Actions are pinned to fixed versions.

## Setup the manager does once

1. Settings > Actions > General: allow GitHub Actions to create pull
   requests.
2. Create the `new-member` label.
3. Add each new member to the repository as a collaborator with **Read**
   access before they submit. Read is enough to open an issue.

## Open questions and risks

- **Downloading the attachment, the one thing to prove first.** In a private
  repository, files attached to issues are only visible to people with
  access, and GitHub doesn't document whether a workflow's own token can
  download them. The first step of building this is a small test. If it can't,
  the alternatives are:
  - a personal access token stored as a repository secret (works, but needs
    renewing yearly);
  - the member pastes the profile text into the issue instead of attaching it
    (the form can offer a "copy" button), with the photo attached as an
    image, which hits the same question;
  - the member uploads the `.zip` with Add file > Upload files, which opens a
    pull request directly. That needs **Write** access, so it suits only
    members the manager trusts with it.
- **Everyone needs a GitHub account.** For people who don't want one, the
  current route still works: they email the `.zip`, and the manager runs
  `add-person.py --zip`.
- **Pull requests opened by a workflow don't start other workflows**
  (GitHub's guard against loops), so `build-site.yml` won't check them. That
  doesn't matter here, since *propose* builds the site itself before opening
  the pull request, and the build runs again after merging.
- **Cost:** a private repository gets 2,000 free Actions minutes a month on
  GitHub's free plan. Each submission takes about two minutes, and each
  rebuild about one.
