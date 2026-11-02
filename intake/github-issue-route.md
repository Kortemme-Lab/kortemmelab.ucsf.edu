# Adding new members through a GitHub issue

New members make their profile with the form, attach the `.zip` to a GitHub
issue, and a workflow turns it into a pull request. A website manager merges
the pull request, and the website rebuilds itself.

## What the member does

1. Opens **Issues > New issue > New lab member**. At the top of that issue
   form is a link to the profile form (`intake/profile-form.html`). They
   download it, open it in their browser, fill it in, and click Save. That
   gives them `their-name-profile.zip`.
2. Puts their name in the issue's title, drags the `.zip` into the box, ticks
   that they're happy for it to be published, and clicks Create.
3. Waits a minute or two for the reply on the issue. It either links to their
   pull request, or says what to fix. To fix something, they save a new `.zip`
   from the form and edit the issue to attach it. The check runs again, and
   the pull request updates itself.

The profile form's Save message links to the issue form too, so they can
also start from the form.

## What the website manager does

Open the pull request (it's linked from the issue), look at the profile and
photo under *Files changed*, and **merge** it. That's all: the issue closes,
and `build-site.yml` rebuilds `docs/` and commits it. To ask for changes,
comment on the issue instead.

## What happens in between

`.github/workflows/new-member.yml` runs when a *New lab member* issue is
opened, edited or reopened. It uses `scripts/new-member-issue.py` for the
GitHub parts and `scripts/add-person.py --zip` for the rest:

1. **Get the .zip.** It finds the newest `.zip` attached to the issue and
   downloads it.
2. **Check it,** exactly as `add-person.py --zip --dry-run` would.
3. **Add them on a branch** of their own, `new-member/issue-N`, made fresh
   from `main`. It runs `add-person.py --zip`, which files the profile and
   photo and draws their publication list, then builds the whole site to make
   sure it still works. It commits only the `content/` changes. `docs/` is
   left out on purpose: it's rebuilt after merging, so two people's pull
   requests can't collide in the generated pages.
4. **Open the pull request,** *Add Jane Doe to the website*. It includes their
   photo, the number of papers, anything worth a look, and "Closes #N".
5. **Comment on the issue** with the result. It's always the same single
   comment, updated each time.

## Setting it up (once)

1. **Let workflows open pull requests:** Settings > Actions > General >
   *Workflow permissions* > tick **Allow GitHub Actions to create and approve
   pull requests**. Without it, the issue comment says this is missing.
2. **Give each new member access** before they submit: Settings >
   Collaborators > Add people, with **Read** access. Read is enough to open an
   issue, and the workflow ignores issues from anyone without access.
3. **Try it once** yourself: open a *New lab member* issue with a test `.zip`.
   You can make one in the form with ORCID's test researcher, Josiah Carberry
   (0000-0002-1825-0097). Then close the pull request without merging and
   delete its branch.

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

The workflow tries its own token first, then `INTAKE_TOKEN`.

## Safety

The `.zip` and the issue text come from outside, so:

- **Only collaborators' issues are handled.** That's everyone, in a private
  repository, but the check stays in place if the repository is ever made
  public.
- **The issue's text is never run.** It reaches `new-member-issue.py` as an
  environment variable and is only parsed there, never put into a shell
  command.
- **Only `github.com` attachment links are downloaded,** up to 20 MB, and only
  if what comes back really is a `.zip`.
- **The `.zip` is checked before anything is written.** One profile and one
  photo with the same name, in the two expected folders, real image data, and
  nothing else.
- **The workflow can't publish anything.** It pushes only its own
  `new-member/issue-N` branch. Only a person's merge changes `main`.

## Good to know

- **Two submissions at once** can both touch `content/bibliography.json`. If
  merging the second says there's a conflict, edit its issue (any small
  change will do), and the pull request is rebuilt from the latest `main`.
- **Someone already on the website** (same file name) is turned away with a
  note: their existing profile needs updating by hand instead.
- **Pull requests opened by a workflow don't start other workflows,** so
  `build-site.yml` doesn't check the pull request itself. It doesn't need to:
  `new-member.yml` has already built the site with the new person on it, and
  `build-site.yml` runs after the merge.
- **Without a GitHub account,** members can still email the `.zip` to a
  website manager, who runs `python3 scripts/add-person.py --zip …` (see the
  README).
- **Cost:** GitHub's free plan includes 2,000 Actions minutes a month for
  private repositories. A submission takes about two minutes, a rebuild about
  one.
