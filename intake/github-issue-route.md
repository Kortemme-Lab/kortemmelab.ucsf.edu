# Profiles through GitHub issues: joining, updating, leaving

Lab members add or change their own profiles by opening a GitHub issue. A
workflow checks what they sent and turns it into a pull request; a website
manager merges it, and the website rebuilds itself. There are three issue
forms (Issues > New issue):

| Issue | For | What it takes |
|---|---|---|
| **New lab member** | someone joining | the `.zip` saved by the profile form |
| **Add papers** | current members and alumni with new papers | their name and the DOIs; no form needed |
| **Update my profile** | current members and alumni: any other change, or leaving the lab | the `.zip` from the form's *Update my profile* mode |

## What the member does

**Joining:** they open *New lab member*. At the top of it is a link to the
profile form (`intake/profile-form.html`): they download it, open it in their
browser, fill it in, and click Save. They put their name in the issue's title,
drag in the `.zip`, tick that they're happy for it to be published, and click
Create.

**Adding new papers:** they open *Add papers*, fill in their name as it
appears on the website, paste the DOIs (or arXiv IDs), and click Create. No
form, no download.

**Changing anything else** (position, summary, photo, links, removing a
paper):
1. They open *Update my profile*, which links to their profile file. They
   find their name among the current members or alumni and download it.
2. In the profile form they choose **Update my profile** and pick that file.
   Every field fills in, with their papers listed and ticked.
3. They change what they like and save. The `.zip` is named
   `their-name-profile-update.zip`. They drag it into the issue.

**Leaving the lab:** the same as changing anything else, but in the form they
tick **I've left the lab, or I'm leaving it** and give the year and what
they're doing next. The pull request moves their profile to Lab Alumni.

Either way, a reply appears on the issue within a minute or two. It either
links to the pull request and sums up what changes, or says what to fix. To
fix something, they edit the issue (a new `.zip`, different DOIs). The check
runs again, and the pull request updates itself.

## What the website manager does

Open the pull request (it's linked from the issue). Look at the changes
under *Files changed*, including the photo, and read the summary at the top.
Then **merge** it. The issue closes, and `build-site.yml` rebuilds `docs/`
and commits it. To ask for changes instead, comment on the issue.

**Check who sent it.** The pull request compares the GitHub account that
opened the issue with the GitHub link already on that profile:

- **✓ match:** it's them.
- **⚠ mismatch:** someone else's account. Check it's really them, or someone
  they asked, such as a co-author adding a paper.
- **No link to compare:** most profiles have no GitHub link yet. Check the
  change looks right for that person. Once someone has added their GitHub link,
  their later updates are checked automatically.

The comparison uses the profile as it is on the website, not the submission,
so putting your own account into someone else's `.zip` doesn't get past it.

## What happens in between

`.github/workflows/profile-submission.yml` runs when any of the three is
opened, edited or reopened. It uses `scripts/profile-issue.py` for the GitHub
parts and `scripts/add-person.py` for the rest:

1. **Read the issue.** It finds the newest `.zip` attached and downloads it.
   For Add papers, it reads the name and DOIs instead.
2. **Check the submission,** as `add-person.py --dry-run` would. A new
   profile mustn't exist yet. An update must match a profile that does exist,
   and must actually change something. A `.zip` from the wrong mode is turned
   away with a note saying which issue it belongs on.
3. **Make the change on a branch** of its own, `profile/issue-N`, made fresh
   from `main`. A new profile is filed. An update is **merged** into the
   existing profile: only the fields the form edits are replaced. Extra
   links, the old-site records and anything added by hand are kept, and so is
   the photo unless a new one was sent. A replaced photo's old file is
   removed. A profile given an end year moves to `content/alumni/`. Its file
   name, and so its web address, never changes. Papers are checked at doi.org,
   and the publication lists are redrawn. Then the whole site is built, to be
   sure it still works. Only `content/` is committed; `docs/` is rebuilt
   after merging, so two pull requests can't collide in the generated pages.
4. **Open the pull request:** "Add Jane Doe to the website", "Update Jane
   Doe's profile" or "Add papers to Jane Doe's profile". It shows what changes,
   the photo, the identity check, anything worth a look, and "Closes #N".
5. **Comment on the issue** with the result. It's always one comment, updated
   each time.

## Setting it up (once)

1. **Let workflows open pull requests:** Settings > Actions > General >
   *Workflow permissions* > tick **Allow GitHub Actions to create and approve
   pull requests**. Without it, the issue comment says this is missing.
2. **Give each member access** before they submit: Settings > Collaborators >
   Add people. The workflow ignores issues from anyone without access.

   **What that access allows, for now:** this repository belongs to a
   personal account, and on a personal account every collaborator can also
   *push* to it. Nothing in GitHub stops a collaborator from changing `main`
   directly. The pull-request review only works because people use it. Moving
   the repository to a GitHub **organization** (free) fixes this: there,
   members can be given **Read** access, which is enough to open issues but
   not to push. See *Next steps* below.
3. **Try it once** yourself, with each of the three issues. To make a test `.zip`
   in the form, use ORCID's test researcher, Josiah Carberry
   (0000-0002-1825-0097), or load and change your own profile. Then close the
   pull requests without merging and delete their branches.

### If the reply says it couldn't download the .zip

In a private repository, attachments are visible only to people with access.
GitHub doesn't document whether a workflow's own token counts, which is the
one part of this that couldn't be tested before it ran on GitHub. If the
reply says the download failed:

1. Create a fine-grained personal access token: your GitHub settings >
   Developer settings > Fine-grained tokens > Generate. Give it access to this
   repository only, with **Contents: read**. A one-year expiry is sensible;
   GitHub emails you before it expires.
2. Add it to the repository: Settings > Secrets and variables > Actions > New
   repository secret, named `INTAKE_TOKEN`.
3. Re-run the failed workflow from the link in the issue comment.

The workflow tries its own token first, then `INTAKE_TOKEN`. Adding papers by
DOI needs no download, so it works either way.

## Safety

The `.zip` and the issue text come from outside, so:

- **Only collaborators' issues are handled,** which matters if the
  repository is ever public.
- **The issue's text is never run.** It reaches `profile-issue.py` as an
  environment variable and is only parsed there, never put into a shell
  command.
- **Only `github.com` attachment links are downloaded,** up to 20 MB, and only
  if what comes back really is a `.zip`.
- **The `.zip` is checked before anything is written:** one profile, one
  photo with the same name, and optionally a small `submission.json` saying
  it's an update. All must be in the expected folders, with real image data.
  Anything else stops it.
- **The workflow can't publish anything.** It pushes only its own
  `profile/issue-N` branch. Only a person's merge changes `main`.

## Good to know

- **Two submissions at once** can both touch `content/bibliography.json`. If
  merging the second says there's a conflict, edit its issue (any small
  change will do), and the pull request is rebuilt from the latest `main`.
- **Alumni on the roster only** (`profile_page: false`, with no page of their
  own) can update too. The pull request notes that deleting that line gives
  them a profile page.
- **Pull requests opened by a workflow don't start other workflows,** so
  `build-site.yml` doesn't check the pull request itself. The submission
  workflow has already built the site with the change, and `build-site.yml`
  runs after the merge.
- **Without a GitHub account,** members can still email the `.zip` to a
  website manager, who runs `python3 scripts/add-person.py --zip …`. Papers can
  be added with `python3 scripts/add-person.py --add-papers "Jane Doe" --dois "10.…"`.
- **Cost:** GitHub's free plan includes 2,000 Actions minutes a month for
  private repositories. A submission takes about two minutes, a rebuild about
  one.

## Next steps (planned)

1. **Move the repository to a GitHub organization,** so members get Read
   access instead of push access (see above). GitHub redirects the old
   address. Afterwards, update the `blonn25/kortemmelab.ucsf.edu` links in
   `.github/ISSUE_TEMPLATE/*.yml` and in `REPO` in `intake/profile-form.html`.
2. **Publish the site with GitHub Pages** (from `/docs`). The issue forms can
   then link straight to the live profile form, with no download.
3. **"Find me" in the profile form:** once the site is on Pages, the build
   can publish a small list of profiles that the form reads. Updating then
   becomes "pick your name" instead of downloading your profile file.
