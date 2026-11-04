# Kortemme Lab website

The source of the Kortemme Lab website. Lab members, start just below.
Website managers, see [For website managers](#for-website-managers).

## For lab members

Everything is done with an issue form here on GitHub. Pick what you want to
do:

| I want to… | Open this form | Before you open it |
|---|---|---|
| add myself to the website | [**New lab member**](https://github.com/Kortemme-Lab/kortemmelab.ucsf.edu/issues/new?template=new-member.yml) | make your `.zip` in the [profile form](https://kortemme-lab.github.io/kortemmelab.ucsf.edu/profile-form.html): *I'm new to the lab* |
| add papers or change my profile (members and alumni) | [**Update my profile**](https://github.com/Kortemme-Lab/kortemmelab.ucsf.edu/issues/new?template=update-profile.yml) | make your `.zip` in the [profile form](https://kortemme-lab.github.io/kortemmelab.ucsf.edu/profile-form.html): *Update my profile*, then pick your name |
| say I'm leaving the lab | [**Update my profile**](https://github.com/Kortemme-Lab/kortemmelab.ucsf.edu/issues/new?template=update-profile.yml) | the same, ticking *I've left the lab* |
| share lab news | [**Add news**](https://github.com/Kortemme-Lab/kortemmelab.ucsf.edu/issues/new?template=add-news.yml) | nothing |
| add photos to the gallery | [**Add photos to the gallery**](https://github.com/Kortemme-Lab/kortemmelab.ucsf.edu/issues/new?template=add-photos.yml) | nothing |

### How it works

1. **Fill in the form** and click **Create**. For a profile, drag in the
   `.zip` the profile form saved.
2. **Within about two minutes, a reply appears on your issue.** It either
   links to a pull request (your change, ready for review: you're done), or
   says what to fix.
3. **A website manager publishes it.** Your issue closes by itself once it's
   live.

**To fix or change something,** edit your issue (the ⋯ menu on its first
post > *Edit*) instead of opening a new one. The check runs again.

**First time?** You need a GitHub account with access to this repository; ask
a website manager. Without access, the forms don't respond. No GitHub account?
Email your `.zip`, news or photos to a website manager instead.

### Good to know

- **The profile form** runs in your browser and keeps your answers until you
  save. Nothing you type leaves your computer, except your ORCID iD and DOIs,
  which are looked up online. When updating, only what you change is
  replaced.
- **Papers:** click *Find my papers on ORCID*, or paste DOIs or arXiv IDs
  under *Other papers*. Untick a paper to take it off your profile.
- **Education:** one degree per line, e.g. `B.S., Chemical Engineering,
  Northwestern University`.
- **Add your GitHub link** to your profile: later updates are then checked
  against it.
- **Leaving the lab:** give the year and what you're doing next. You move to
  Lab Alumni, and can update your position the same way at any time.
- **News:** one sentence, as it should read on the website, using first
  names: "Radhika wins a 2024 Mary Anne Koda-Kimble Seed Award for
  Innovation".
- **Photos:** up to 10, and the caption goes on the first. The website's copies
  have their location data removed, but the photos attached to your issue are
  public as uploaded. If location matters, turn it off before attaching (on
  an iPhone: *Share* > *Options* > *Location*).
- **Preprints:** if a new paper is the published version of a preprint, the
  profile form asks whether to *show only the published paper* (the preprint
  then disappears everywhere on the website, including co-authors' pages) or
  *keep both*. If your preprint is still listed after the published paper
  appears, say so under *Anything else* on an *Update my profile* issue, with
  both DOIs.

## For website managers

The website is plain HTML in `docs/`, built from Markdown in `content/` by
`scripts/build-site.py`, and published by GitHub Pages at
<https://kortemme-lab.github.io/kortemmelab.ucsf.edu/>. The repository is
public, so anything committed to it is public too. Day to day, the job is
reviewing submissions; everything else is in the sections after that.

### Reviewing submissions

1. **Open the pull request** linked from the issue's reply. Its description
   says what changes, shows any new photos, lists any preprints it replaces,
   and notes anything worth a look.
2. **For a profile, check who sent it.** The description compares the issue's
   author with the GitHub link on the profile: **✓** it's them; **⚠** someone
   else (make sure it's really them, or someone they asked); or *no GitHub
   link to compare with* (usual for older profiles: check it looks right).
3. **Look at *Files changed*.** To fix wording yourself, edit the file there
   (⋯ > *Edit file*) before merging.
4. **Merge**, and delete the branch. The issue closes, and the site rebuilds
   within a couple of minutes. `git pull` before your own next edits.

- **To ask for changes,** comment on the issue (not the pull request), so the
  member sees it. Their edit updates the pull request.
- **To turn one down,** close the pull request, then the issue, with a comment.
- **Several at once:** merge one at a time, a couple of minutes apart. After
  each merge, the other open submissions are remade from the updated website
  by themselves (`refresh-submissions.yml`), so they don't conflict. One with
  someone's own commit on it is left alone: edit its issue to remake it, or
  resolve the conflict by hand.

| If the reply on the issue says… | Do this |
|---|---|
| it couldn't open the pull request | turn on the setting under *Setup*, below, then re-run the workflow from the link in the reply |
| it couldn't download the `.zip` | only happens if the repository is private: see `intake/github-issue-route.md` |
| something went wrong | open the run from the link in the reply and read the failed step |

**Setup** (done once): in the repository's and the organization's Settings >
Actions > General, tick **Allow GitHub Actions to create and approve pull
requests**. Give lab members **Read** access through the Kortemme-Lab
organization (a team makes it easy), alumni **Read** as outside
collaborators, and website managers **Write** or **Maintain**. Read is enough
to submit, but not to push, so nothing reaches the website without a merge.
How the route works and its safety measures: `intake/github-issue-route.md`.

<details>
<summary><strong>Building and publishing the website</strong></summary>

#### Building it locally

Edit `content/`, then:

```bash
python3 scripts/render-publications.py
```

```bash
python3 scripts/build-site.py
```

The first redraws the publication lists (needed only if a `publications:`
list or `content/bibliography.json` changed). The second rebuilds `docs/`
from scratch and stops with a list if any internal link or image is broken.
Then open `docs/index.html`. Only the Python standard library is needed.

#### Automatic rebuilds

`.github/workflows/build-site.yml` runs both whenever `content/`, `theme/` or
the build scripts change on `main`, and commits the result, so `docs/` can't
fall out of step, even after an edit in GitHub's web editor. Because it adds a
commit after yours, `git pull` before starting new work. A failed run shows as
a red cross on the commit, and GitHub emails whoever pushed it. You can also
run it from the Actions tab.

#### What each page is made from

| Page | From |
|---|---|
| Home, News, Gallery, Contact, Meetings, Directions, Join the Lab, Publications | `content/<page>.md` |
| Home's Selected Publications, and Perspectives and Reviews | the DOIs in `featured_publications` / `featured_reviews` in `content/index.md`'s header |
| Current Members | every file in `content/current-members/`, grouped by `role` |
| Lab Alumni | every file in `content/alumni/`, by role then newest first, plus `content/rotation-students.csv` |
| `people/<name>.html` | each person's file, unless it says `profile_page: false` |
| `current---kosuke-seki.html` and the like | forwarding pages for the old site's profile addresses |
| `profile-form.html` | `intake/profile-form.html`; on no menu, linked from the issue forms |
| `profiles.json` | every profile's file, for the profile form's name list |

#### The look, and writing pages

The look is `theme/layout.html` (header, menu, footer) and `theme/site.css`,
following the old theme; the menu is `NAV` near the top of `build-site.py`.
Markdown in `content/` can use headings, paragraphs, lists, `---` rules,
links, images, `**bold**` and `*italic*`. An image alone in its paragraph
becomes a figure, with an `*italic*` line under it as its caption; several in
a row become a photo grid. Raw HTML lines pass through, as for the map and
calendar, and `<div class="columns">` puts a picture beside its text. The
Gallery's carousel (`carousel: true` in `content/gallery.md`, drawn by
`theme/carousel.js`) is just the list of photos in that file, top first.

#### The kortemmelab.ucsf.edu address

1. Ask UCSF IT to change the DNS:
   - a **CNAME** record, `kortemmelab.ucsf.edu` → `kortemme-lab.github.io`,
     replacing the one that points at Weebly;
   - a **TXT** record that verifies the domain. To get it, go to the
     organization's Settings > Pages > *Add a domain* and enter
     `kortemmelab.ucsf.edu`.
2. Once IT confirms, enter `kortemmelab.ucsf.edu` under **Custom domain** in
   the repository's Settings > Pages. GitHub adds `docs/CNAME`, which the
   build keeps; `git pull` afterwards. Tick **Enforce HTTPS** once the
   certificate is ready (up to a day).

Don't set the custom domain before the DNS changes, or visitors are sent to
the old Weebly site. Links to the github.io address keep working afterwards.
Then cancel the Weebly site: old profile addresses keep working through the
forwarding pages.

</details>

<details>
<summary><strong>Where everything is</strong></summary>

```
kortemmelab.ucsf.edu/
├── content/               everything the site says
│   ├── *.md               the pages on the site's menu
│   ├── current-members/   one file per current lab member
│   ├── alumni/            one file per alumnus
│   ├── images/            every photo: people/ (headshots), gallery/, and the rest
│   ├── bibliography.json  every paper cited on the site, keyed by DOI
│   ├── journal-abbreviations.json   Nature-style journal abbreviations
│   ├── rotation-students.csv   past rotation students, for Lab Alumni
│   └── archive/           old pages kept but not in use
├── theme/                 the look: layout.html, site.css, carousel.js, fonts/
├── scripts/               build-site.py, render-publications.py, bibliography.py,
│                          add-person.py, add-content.py, submission-issue.py;
│                          the rest made the copy of the old site
├── intake/                profile-form.html, how the issue route works
│                          (github-issue-route.md), the profile template, and
│                          questions for a Google form instead
├── docs/                  the website itself, generated: don't edit, rebuild
├── .github/               the issue forms, and the workflows: build-site.yml,
│                          submission.yml, refresh-submissions.yml
└── archive/               the old Weebly site and how it was moved (see its README)
```

**The folder a person's file sits in is their status,** so graduating
someone by hand is a move to `content/alumni/` (an *Update my profile* with an
end year does it for you). `content/current-members.md` and
`content/lab-alumni.md` are the old roster pages, kept for reference; the
rosters are generated from the two folders.

</details>

<details>
<summary><strong>Publications and the bibliography</strong></summary>

Every publication list is drawn from `content/bibliography.json`: every paper
cited on the site, keyed by DOI, in CSL-JSON (the format Zotero and Pandoc
read), as each publisher registered it. Hand-made or corrected entries have a
`note`.

- **A person's list** is the DOIs in the `publications:` field of their file,
  newest first.
- **Tanja's list and the Publications page** are every paper with her as an
  author; the page lists preprints first, then by year.
- **A preprint is shown until it's published.** Once it's linked to its
  published version (by its DOI record, a member's answer in the profile
  form, or by hand), the published paper replaces it on every list.
- **The style is Nature's,** except that people's pages list every author and
  the Publications page the first five, then "et al.". Co-first authors
  (`"co-first": true` on those authors in the entry) are marked with `*`.
  Journal abbreviations are in `content/journal-abbreviations.json`.

**To add a paper,** put its DOI in the `publications:` list of each lab member
who wrote it and run `python3 scripts/render-publications.py` (or just push).
It looks the DOI up, adds it to the bibliography and redraws the lists, which
sit between `publications:start` and `publications:end` markers: anything
edited inside them is overwritten. **To remove one,** delete its DOI from the
person's list; to take it off the Publications page too, delete its
bibliography entry.

**To link a preprint to its published version** when doi.org doesn't, add to
the preprint's entry in `bibliography.json`:

```json
"relation": {"is-preprint-of": ["10.1002/adma.202500872"]},
```

with the published DOI in lower case (or add it to an existing `relation`
list), and push. To keep a pair listed separately instead, add
`"keep-preprint": ["10.1002/adma.202500872"]`. Now and then, run
`python3 scripts/render-publications.py --check-preprints`: it asks doi.org
whether any preprint has since been published and adds those links (it never
removes one).

One paper has no DOI record anywhere, "SAT-based protein design" (ICCAD
2009), so its entry was made by hand. With every author listed, the largest
consortium papers run to about a hundred names.

</details>

<details>
<summary><strong>Changing people, news and photos by hand</strong></summary>

#### The profile format

Every profile follows `intake/profile-template.md`: `name`, `role`,
`summary`, `photo`, `links`, `education`, `publications` and so on in the
header, and a longer bio below it. Alumni also have `current_position`, and
`position_after_lab` once they've moved on from their first job. Education
reads *Degree, Subject, Institution*: B.S., B.A., M.S., M.Sc. (European
master's), Ph.D., German degrees with the equivalent in brackets ("Dr. rer.
nat. (Ph.D.)"), full institution names, and a city only for US campuses that
use one. `add-person.py` tidies submissions into this style, but a European
"Master of Science" becomes M.S., so change it to M.Sc. in the pull request.

#### From a .zip, by email

For someone without a GitHub account:

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip --dry-run
```

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip
```

It handles new profiles and updates alike (only the fields the form edits are
replaced, and an end year moves the person to alumni), checks every DOI, and
redraws the publication lists. To add papers directly:

```bash
python3 scripts/add-person.py --add-papers "Jane Doe" --dois "10.1126/science.abc0881 arXiv:2204.13048"
```

Add `--replace-preprints` if one is the published version of a preprint on
the website.

#### News and photos

```bash
python3 scripts/add-content.py news --month June --year 2025 --text "Colin receives tenure" --link https://…
```

```bash
python3 scripts/add-content.py photos --caption "Lab retreat 2026" ~/Downloads/a.jpg ~/Downloads/b.jpg
```

News goes into `content/news.md` in date order. Photos go at the top of the
gallery, upright, at most 1600 pixels, and without their metadata (no GPS
location). Photos need Pillow (`python3 -m pip install pillow`). Both take
`--dry-run`. If you edit `content/news.md` or `content/gallery.md` by hand
instead, strip a photo's location yourself.

#### From a Google or Microsoft form

Set up a form with the questions in `intake/form-questions.md` (keep the
opening words of each question title). Export the responses to
`intake/responses.csv`, put the headshots in `intake/photos/`, and run
`python3 scripts/add-person.py --csv intake/responses.csv`, first with
`--dry-run`. It reports mistyped ORCID iDs, DOIs that don't resolve, HEIC or
small photos, and skips anyone already on the website. The CSV and photos
stay out of git. `intake/example-responses.csv` has two fictional responses to
try it with.

</details>

<details>
<summary><strong>The old site</strong></summary>

The website used to run on Weebly. `archive/` keeps a cleaned-up copy of it,
the old pages that aren't in use (`content/archive/`), notes on how every
profile and citation was moved, and how to capture the old site again. The
website doesn't need any of it. See [`archive/README.md`](archive/README.md).

</details>
