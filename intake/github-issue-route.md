# Submitting through GitHub issues: profiles, news and photos

Lab members add or change their own profiles by opening a GitHub issue. A
workflow checks what they sent and turns it into a pull request; a website
manager merges it, and the website rebuilds itself. There are two issue
forms (Issues > New issue):

| Issue | For | What it takes |
|---|---|---|
| **New lab member** | someone joining | the `.zip` saved by the profile form |
| **Update my profile** | current members and alumni: new papers, any other change, or leaving the lab | the `.zip` from the form's *Update my profile* mode |
| **Add news** | anyone with news for the News page | a month, a year, one sentence and an optional link |
| **Add photos to the gallery** | anyone with photos for the gallery | up to 10 photos, an optional caption, and a tick that everyone pictured agrees |

News and photos need no form of our own: the issue form is enough. The news
item goes into `content/news.md` in date order; the photos go at the top of
`content/gallery.md`, saved in `content/images/gallery/` after being turned
upright, scaled down to at most 1600 pixels and stripped of their metadata
(including GPS location), by `scripts/add-content.py`. The workflow installs
Pillow, the standard Python imaging library, for that step only. The photos
attached to the issue itself stay as they were uploaded, and are as public as
the issue.

## What the member does

**Joining:** they open *New lab member*. At the top of it is a link to the
profile form, hosted on the website but on none of its menus
(https://kortemme-lab.github.io/kortemmelab.ucsf.edu/profile-form.html,
copied from `intake/profile-form.html` by the build). They fill it in and
click Save. They put their name in the issue's title,
drag in the `.zip`, tick that they're happy for it to be published, and click
Create.

**Adding papers, or changing anything else** (position, summary, photo,
links, removing a paper):
1. They open *Update my profile*, which links to the same profile form.
2. There they choose **Update my profile** and pick their name. The list
   comes from `profiles.json`, which the build writes next to the form with
   every profile's file, so it matches the website. Every field fills in,
   with their papers listed and ticked. (Opened from a downloaded copy
   instead, the form can't read that list, and asks for the profile's `.md`
   file.)
3. They change what they like, adding new papers from ORCID or by DOI, and
   save. If a new paper is the published version of a preprint, the form asks
   whether it replaces the preprint. The `.zip` is named
   `their-name-profile-update.zip`. They drag it into the issue.

**Leaving the lab:** the same, but in the form they
tick **I've left the lab, or I'm leaving it** and give the year and what
they're doing next. The pull request moves their profile to Lab Alumni.

Either way, a reply appears on the issue within a minute or two. It either
links to the pull request and sums up what changes, or says what to fix. To
fix something, they edit the issue and attach a new `.zip`. The check runs
again, and the pull request updates itself.

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

For profiles, in more detail: `.github/workflows/submission.yml` runs when
any of the forms' issues is opened, edited or reopened. It uses
`scripts/submission-issue.py` for the GitHub
parts and `scripts/add-person.py` for the rest:

1. **Get the .zip.** It finds the newest `.zip` attached and downloads it.
2. **Check the submission,** as `add-person.py --dry-run` would. A new
   profile mustn't exist yet. An update must match a profile that does exist,
   and must actually change something. A `.zip` from the wrong mode is turned
   away with a note saying which issue it belongs on.
3. **Make the change on a branch** of its own, `submission/issue-N`, made fresh
   from `main`. A new profile is filed. An update is **merged** into the
   existing profile: only the fields the form edits are replaced. Extra
   links, the old-site records and anything added by hand are kept, and so is
   the photo unless a new one was sent. A replaced photo's old file is
   removed. A profile given an end year moves to `content/alumni/`. Its file
   name, and so its web address, never changes. Papers are checked at doi.org.
   When the member confirms, in the profile form's question, that a published
   paper replaces a preprint, the preprint is linked to it in
   `content/bibliography.json`, but only if the published paper's DOI record
   names that preprint. The preprint then disappears from every page. Then
   the publication lists are redrawn, and the whole site is built, to be sure
   it still works. Only `content/` is committed; `docs/` is rebuilt
   after merging, so two pull requests can't collide in the generated pages.
4. **Open the pull request:** "Add Jane Doe to the website" or "Update Jane
   Doe's profile". It shows what changes, any preprints it replaces,
   the photo, the identity check, anything worth a look, and "Closes #N".
5. **Comment on the issue** with the result. It's always one comment, updated
   each time.

## Setting it up (once)

1. **Let workflows open pull requests:** Settings > Actions > General >
   *Workflow permissions* > tick **Allow GitHub Actions to create and approve
   pull requests**. Without it, the issue comment says this is missing.
2. **Give each member access** before they submit. Anyone can open an issue
   on a public repository, but the workflow ignores issues from people
   without access, so strangers can't fill the repository with branches and
   pull requests. The repository belongs to the **Kortemme-Lab**
   organization, so:
   - lab members join the organization, with **Read** access to this
     repository (easiest through a team);
   - alumni are added as outside collaborators with **Read**;
   - website managers get **Write** or **Maintain**, so they can merge.

   **Read** is enough to open issues but not to push, so nothing changes
   `main` without a manager merging a pull request. The organization's own
   Settings > Actions must also allow workflows to create pull requests, or
   the repository setting in step 1 can't be turned on.
3. **Try it once** yourself, with each of the two issues. To make a test `.zip`
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

- **Only issues from people with access are handled** (organization members
  and collaborators), which matters because the repository is public. The
  workflow's first step checks this. GitHub reports a member whose
  membership is private (the default) as a mere contributor, so anyone not
  reported as a member is looked up as a collaborator, which includes members
  with access through a team. Anyone else's issue is left alone, with no
  reply.
- **The issue's text is never run.** It reaches `submission-issue.py` as an
  environment variable and is only parsed there, never put into a shell
  command.
- **Only `github.com` attachment links are downloaded,** up to 20 MB, and only
  if what comes back really is a `.zip`.
- **The `.zip` is checked before anything is written:** one profile, one
  photo with the same name, and optionally a small `submission.json` saying
  it's an update. All must be in the expected folders, with real image data.
  Anything else stops it.
- **The workflow can't publish anything.** It pushes only its own
  `submission/issue-N` branch. Only a person's merge changes `main`.

## Good to know

- **Several submissions at once** each get their own branch and pull
  request, so they never overwrite each other. Profiles of different people
  never clash, but news from the same month, gallery photos and new papers go
  in shared files (`content/news.md`, `content/gallery.md`,
  `content/bibliography.json` and the publication lists). So after every push
  to `main` that changes `content/`, `refresh-submissions.yml` asks
  `submission.yml` to redo every other open submission from the latest
  `main` (a `workflow_dispatch` with its issue number), as if its issue had
  been edited: checked again, branch rebuilt, pull request and reply updated.
  Merge one, wait a couple of minutes, merge the next. A pull request with
  anyone's commits besides the workflow's is left alone; edit its issue to
  remake it anyway (which drops those commits), or resolve it by hand.
- **Alumni on the roster only** (`profile_page: false`, with no page of their
  own) can update too. The pull request notes that deleting that line gives
  them a profile page.
- **Pull requests opened by a workflow don't start other workflows,** so
  `build-site.yml` doesn't check the pull request itself. The submission
  workflow has already built the site with the change, and `build-site.yml`
  runs after the merge.
- **Without a GitHub account,** members can still email the `.zip` to a
  website manager, who runs `python3 scripts/add-person.py --zip …`. A manager
  can also add papers by hand, with `python3 scripts/add-person.py --add-papers
  "Jane Doe" --dois "10.…"` (add `--replace-preprints` if one replaces a
  preprint on the website).
- **Cost:** GitHub's free plan includes 2,000 Actions minutes a month for
  private repositories. A submission takes about two minutes, a rebuild about
  one.

## Next steps (planned)

Nothing planned right now. Once the custom domain (kortemmelab.ucsf.edu) is
set up, the github.io links in the issue forms and the README keep working:
GitHub forwards them to the custom domain.
