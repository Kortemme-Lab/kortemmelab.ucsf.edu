# Kortemme Lab website

The source of the Kortemme Lab website, kortemmelab.ucsf.edu.

**Lab members:** this page explains how to put yourself on the website, add
your papers, update your profile, record that you're leaving the lab, share
lab news, and add photos to the gallery. It's all done with GitHub issue
forms (and, for profiles, a short form of our own); no coding is needed.

**Website managers:** how the site is built and run is
[further down](#for-website-managers).

## For lab members

- [Before you start](#before-you-start)
- [Joining the lab](#joining-the-lab)
- [Adding papers or changing your profile](#adding-papers-or-changing-your-profile)
- [Leaving the lab](#leaving-the-lab)
- [Sharing news](#sharing-news)
- [Adding photos to the gallery](#adding-photos-to-the-gallery)
- [Preprints and their published versions](#preprints-and-their-published-versions)
- [After you submit](#after-you-submit)

### Before you start

Everything goes through a GitHub issue form. A website manager reviews what
you send and publishes it, and the website then updates by itself.

| To… | Open this issue | You'll need |
|---|---|---|
| put yourself on the website when you join | [**New lab member**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=new-member.yml) | the profile form |
| add new papers to your profile, or change anything else on it (current members and alumni alike) | [**Update my profile**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=update-profile.yml) | the profile form and your current profile file |
| tell us you're leaving the lab | [**Update my profile**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=update-profile.yml) | the same, ticking *I've left the lab* |
| share lab news: an award, a new job, a graduation, a grant | [**Add news**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=add-news.yml) | nothing else: just the form |
| add photos to the gallery | [**Add photos to the gallery**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=add-photos.yml) | your photos |

All of them are also under the repository's **Issues** tab > **New issue**.

**You need a GitHub account,** and a website manager must have added you to
this repository; ask one to. No GitHub account? Make your `.zip` with the
profile form anyway and email it to a website manager (or email them your
news or photos).

**The profile form** is a single file. Open
[it on GitHub](https://github.com/blonn25/kortemmelab.ucsf.edu/blob/main/intake/profile-form.html),
click the **download** button (↓, the *Download raw file* icon at the top
right of the file), and open the downloaded file in your web browser. It
needs nothing installed. Nothing you type leaves your computer, except your
ORCID iD and DOIs, which are looked up at orcid.org and doi.org. Your answers
are kept in your browser until you save, so you can stop and come back.

### Joining the lab

1. Download and open the profile form (above).
2. Under **Start here**, choose **I'm new to the lab**.
3. Fill in **About you**: your name as it should appear on the website, your
   pronouns if you'd like them shown, your role, your program, the year you
   joined, and any co-mentors.
4. Write a **research summary** (one sentence on what you work on, shown under
   your name), and optionally a longer bio. Then list your **education**, one
   degree per line: the degree, the subject, then the university, e.g.
   `B.S., Chemical Engineering, Northwestern University`. Write degrees as
   B.S., B.A., M.S., M.Sc. or Ph.D. (if you don't, they're tidied into that
   style when your profile is added).
5. Add a **headshot**: a clear, recent JPG or PNG, ideally at least 400 × 400
   pixels. The website shows it square, so once it's loaded, **drag the photo**
   inside the square to choose what's shown, and use **Zoom** to frame it
   closer (*Reset* starts over). What's in the square is exactly what's saved.
   iPhone HEIC photos need converting first; the form says how.
6. Under **Contact and links**, add your email (it's only saved if you tick
   *Show my email on my profile*), your ORCID iD, and any Google Scholar,
   website or GitHub links. Do add your GitHub link: later updates to your
   profile are then checked against it automatically.
7. Under **Publications**, click **Find my papers on ORCID** and tick the ones
   to list. For anything missing from ORCID, paste its DOI or arXiv ID under
   *Other papers* and click **Look these up**. If one of your papers is the
   published version of a preprint, the form asks about it; see
   [Preprints and their published versions](#preprints-and-their-published-versions).
8. Check the **Preview**, then click **Save my profile**. You get one file,
   `your-name-profile.zip`.
9. Open a [**New lab member**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=new-member.yml)
   issue. Put your name in the title (`New lab member: Jane Doe`), drag the
   `.zip` into *Your profile .zip*, tick the publishing box, and click
   **Create**.

### Adding papers or changing your profile

For current members and alumni alike: new papers, a new position, a new
photo, a different summary, links, or papers to take off your profile.

1. **Download your current profile.** On GitHub, open
   [current members](https://github.com/blonn25/kortemmelab.ucsf.edu/tree/main/content/current-members) or
   [alumni](https://github.com/blonn25/kortemmelab.ucsf.edu/tree/main/content/alumni),
   click your file (e.g. `jane-doe.md`), and click the **download** button (↓).
2. Download and open the profile form (see [Before you start](#before-you-start)).
3. Under **Start here**, choose **Update my profile**, click *Choose file*,
   and pick the profile you just downloaded. Every field fills in from it,
   and your papers appear under *On your profile now*, all ticked.
4. Change whatever you like:
   - edit any text field;
   - **add new papers:** click *Find my papers on ORCID* and tick the new ones,
     or paste their DOIs under *Other papers* and click *Look these up*. If one
     is the published version of a preprint, answer the form's question about
     it (see [Preprints and their published versions](#preprints-and-their-published-versions));
   - **untick** a paper to take it off your profile;
   - choose a new headshot (and crop it, as when joining), or leave the photo
     field empty to keep the one you have;
   - untick *Show my email on my profile* to remove your email from the website.
5. Check the **Preview**, then click **Save my profile**. You get
   `your-name-profile-update.zip`.
6. Open an [**Update my profile**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=update-profile.yml)
   issue. Put your name in the title (`Profile update: Jane Doe`), drag the
   `.zip` into *Your updated profile .zip*, tick the publishing box, and click
   **Create**.

Only what you changed is replaced. Anything else in your profile stays as it
is, and your page keeps its web address even if you change your name.

### Leaving the lab

Follow [Adding papers or changing your profile](#adding-papers-or-changing-your-profile).
At step 4, under **About you**, tick **I've left the lab, or I'm leaving it**,
and fill in:

- **Year you left (or are leaving):** required.
- **What you're doing now, or next:** e.g. `Assistant Professor, Example University`.
- **Your first position after the lab:** only if you've since moved on from it;
  otherwise leave it empty.

Once it's published, you move from Current Members to Lab Alumni, with your
years and positions on the alumni roster. Alumni can come back the same way
at any time to update their current position.

### Sharing news

1. Open an [**Add news**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=add-news.yml) issue, and
   put a few words in the title (`News: Radhika's seed award`).
2. Choose the **month** and type the **year** it happened.
3. Write the **news** as one sentence, as it should appear on the website,
   using first names as the News page does: "Radhika wins a 2024 Mary Anne
   Koda-Kimble Seed Award for Innovation".
4. Optionally add a **link** to a web page about it (an announcement or
   article); the news item links to it.
5. Click **Create**.

News appears in date order, newest first.

### Adding photos to the gallery

1. Open an [**Add photos to the gallery**](https://github.com/blonn25/kortemmelab.ucsf.edu/issues/new?template=add-photos.yml)
   issue, and put a few words in the title (`Gallery: lab retreat 2026`).
2. Drag up to 10 **photos** (JPG or PNG) into the *Photos* box, and wait for
   each to finish uploading. Put the one you'd like captioned first.
3. Optionally add a **caption**, e.g. "Lab retreat at Asilomar, May 2026". It's
   shown under the first photo.
4. Tick that everyone recognisable in the photos is happy for them to be on
   the website, and click **Create**.

The photos go at the top of the gallery. For the website, they're scaled
down and their location data and other hidden details are removed. The photos
you attach also stay visible on the issue, which anyone can see, so if one was
taken somewhere private, turn its location off before attaching it (on an
iPhone: *Share* > *Options* > turn off *Location*).

### Preprints and their published versions

Preprints are welcome on the website. When one of yours is published, add
the published paper with *Update my profile*. The profile form asks about
each paper whose DOI record names a preprint: under *Published versions of
preprints*, choose **Show only the published paper** or **Keep both**. You
can't save until each is answered; there are buttons to answer them all at
once.

"Show only the published paper" removes the preprint **everywhere it's
listed** on the website: your page, your co-authors' pages, Tanja's page and
the Publications page. A website manager sees which preprints will be
replaced before anything changes. "Keep both" is remembered, so the pair
isn't merged later either.

The website only recognises a pair when the published paper's DOI record
names its preprint. bioRxiv preprints are almost always linked this way;
arXiv ones, and papers whose preprint was posted elsewhere, often aren't. **If
your preprint is still listed after the published paper is on the website,**
say so in the *Anything else* box of an *Update my profile* issue, giving
both DOIs, and a website manager will link them. (Unticking the preprint in
the form only takes it off your own page.)

### After you submit

A check runs as soon as the issue is created and replies on it, usually
within two minutes. The reply either:

- **links to a pull request** (a proposed change to the website) and sums up
  what it changes, e.g. "current position, research summary, 1 paper added".
  Nothing more is needed from you: a website manager reviews it and publishes
  it, and your issue closes by itself once it's published. Or
- **says what to fix**, e.g. a `.zip` attached to the wrong kind of issue, a
  DOI that doesn't exist, or a missing month.

To fix something, or to change your mind before it's published, **edit the
issue**: the ⋯ menu on your issue's first post > *Edit*. Change what's needed
(for a profile, attach a new `.zip` saved again from the form) and click
*Update comment*. The check runs again,
and the pull request updates itself. There's no need to open a new issue.

If the reply says something you don't understand, or nothing appears after a
few minutes, ask a website manager.

## For website managers

The website is plain HTML in `docs/`, built from Markdown files in
`content/` by `scripts/build-site.py`, and published from `docs/` by GitHub
Pages. `archive/` keeps a copy of the old Weebly site for reference. The
repository is public, so anything committed to it is public too.

Day to day, the job is reviewing what lab members submit (profiles, news
and photos), just below.
Everything else is in the dropdowns after it:

- **Building and publishing the website:** building `docs/` locally, the
  automatic rebuild on every push, what each page is made from, the look,
  adding news or photos by hand, and GitHub Pages with the kortemmelab.ucsf.edu
  address.
- **Where everything is:** the repository's layout, and how people's files
  are organized.
- **Publications and the bibliography:** how every publication list is
  drawn, the citation style, and adding, removing or fixing papers by hand.
- **Profiles, and changing people by hand:** the profile format, adding or
  updating people from a `.zip`, by DOI or from a Google Form, and notes on
  the migrated profiles.
- **The old site and its archive:** viewing the old Weebly copy, how it was
  cleaned up and checked, archived pages, its known limitations, and how to
  capture it again.

### Reviewing and publishing submissions

1. **Open the pull request** linked from the issue (or from the **Pull
   requests** tab). Its description says what changes, shows any new photos,
   lists any preprints it replaces, and notes anything worth a look, such as a
   DOI that was left out because it doesn't resolve.
2. **For a profile, check who sent it.** The description compares the GitHub account that
   opened the issue with the GitHub link already on that profile:
   - **✓ Opened by … the GitHub account on this profile:** it's them.
   - **⚠ … but this profile's GitHub link is …:** someone else's account. Make
     sure it's really them, or someone they asked, such as a co-author adding a
     paper.
   - **This profile has no GitHub link to compare with:** usual for older
     profiles. Check the change looks right for that person.
3. **Look at *Files changed*:** the profile text, any new photo, and the
   redrawn publication lists. A profile moving to Lab Alumni shows as a file
   renamed from `current-members/` to `alumni/`. For **news**, it's one line in
   `content/news.md`: check the wording and date. For **photos**, they're new
   files in `content/images/gallery/` (already scaled down, with their
   metadata removed) plus a few lines at the top of `content/gallery.md`:
   check the photos are suitable and the caption reads well. To fix wording
   yourself, edit the file in the pull request (*Files changed* > ⋯ > *Edit
   file*) before merging.
4. **Merge** it (*Merge pull request* > *Confirm merge*), and delete the
   branch when GitHub offers. The issue closes, and the *Build the website*
   workflow rebuilds `docs/` within a couple of minutes. Then `git pull`
   before your own next edits.

To ask for changes, comment on the issue (not the pull request), so the
member sees it. When they edit the issue, the pull request updates. To turn
a submission down, close the pull request without merging, then close the
issue with a comment.

**Linking a preprint to its published version by hand,** when a member
reports a pair the website didn't recognise:

1. In `content/bibliography.json`, find the **preprint's** entry (search for
   its DOI, e.g. `"id": "10.1101/2024.06.21.600123"`), and add a line to it:

   ```json
   "relation": {"is-preprint-of": ["10.1002/adma.202500872"]},
   ```

   with the published paper's DOI, in lower case. If the entry already has
   a `"relation"` line, add the DOI to its list instead.
2. Commit and push. The rebuild workflow redraws every list: the preprint is
   replaced by the published paper on every page it was on, and the
   published paper is looked up at doi.org if it isn't on the website yet.

To undo a replacement, or to keep a pair listed separately when doi.org links
it, add `"keep-preprint": ["10.1002/adma.202500872"]` to the preprint's entry
(the published DOIs that should *not* replace it). Now and then, run
`python3 scripts/render-publications.py --check-preprints`: it asks doi.org
whether any preprint has since been published, and adds those links. It
never removes a link, so confirmed and hand-made ones are safe.

**One-time setup:** Settings > Actions > General > *Workflow permissions* >
tick **Allow GitHub Actions to create and approve pull requests**. Add each
member under Settings > Collaborators before they submit.

| If the reply on the issue says… | Do this |
|---|---|
| it couldn't open the pull request | the setup step just above, then re-run the workflow from the link in the reply |
| it couldn't download the `.zip` | only happens if the repository is private: add an `INTAKE_TOKEN` secret (steps in `intake/github-issue-route.md`), then edit the issue to check again |
| something went wrong | open the run from the link in the reply (Actions tab) and read the failed step |

If merging says there's a **conflict** (two submissions at once can both
touch `content/bibliography.json`), edit the second issue (any small change
will do), and its pull request is rebuilt from the latest `main`.

How the route works, the identity check, its safety measures, and the
planned next steps are in `intake/github-issue-route.md`. A note on access:
this repository belongs to a personal account, so every collaborator can
also push to it directly. Until it moves to a GitHub organization, the review
step relies on people using the issue forms.

<details>
<summary><strong>Building and publishing the website</strong></summary>

#### Building it locally

`content/` holds every page as a Markdown file; `scripts/build-site.py` turns
them into plain HTML in `docs/`. To change the site, edit `content/`, then:

```bash
python3 scripts/render-publications.py
```

```bash
python3 scripts/build-site.py
```

The first redraws publication lists (only needed if a `publications:` list or
`content/bibliography.json` changed). The second rebuilds `docs/` from
scratch and checks every internal link and image; it stops with a list if one
is broken. Then open `docs/index.html` in a browser. No server and nothing to
install: only the Python standard library.

#### Automatic rebuilds

`.github/workflows/build-site.yml` runs on GitHub whenever something in
`content/`, `theme/` or the build scripts changes on `main`. It redraws the
publication lists, rebuilds `docs/`, and commits the result as
*github-actions[bot]*, so the site can't fall out of step with its content,
even after an edit made in GitHub's web editor. If you built the site
yourself before pushing, there's nothing left to commit and it just confirms
the build works. On a pull request it only checks that the site builds and
its links work.

Because it can add a commit after yours, run `git pull` before starting new
work. A failed run (a broken link, a DOI that doesn't resolve) shows as a red
cross on the commit, and GitHub emails whoever pushed it. You can also start a
run from the Actions tab (Build the website > Run workflow).

#### What each page is made from

| Page | From |
|---|---|
| Home, News, Gallery, Contact, Meetings, Directions, Join the Lab, Publications | `content/<page>.md` |
| Home's Selected Publications and Perspectives and Reviews | the DOIs in `featured_publications` / `featured_reviews` in `content/index.md`'s header |
| Current Members | every file in `content/current-members/`, grouped by `role` |
| Lab Alumni | every file in `content/alumni/`, by role and then newest first, plus `content/rotation-students.csv` |
| `people/<name>.html` | each person's file, unless it says `profile_page: false` (17 older alumni who appear on the roster only) |
| `current---kosuke-seki.html` and the like | small pages forwarding the old site's profile addresses to the new ones |
| `profile-form.html` | `intake/profile-form.html`, copied as it is; it's on no menu |

#### The look, and writing pages

The look lives in `theme/layout.html` (the frame around every page: header,
menu, footer) and `theme/site.css`. They follow the old theme: Raleway, the
menu centered between thin rules, teal links. Body text is a shade darker than
the old site's for readability. The menu itself is `NAV` near the top of
`build-site.py`. Pages work on phones; the menu folds into a button.

Markdown in `content/` can use headings, paragraphs (a single line break stays
a line break), `-` and `1.` lists, `---` rules, links, images, `**bold**` and
`*italic*`. An image alone in its paragraph becomes a figure, with an
`*italic*` line under it as its caption, and several in a row become a photo
grid. Lines of raw HTML pass through as they are, which is how the map and
calendar are embedded, and how Contact and Directions put a picture beside its
text (`<div class="columns">`).

The Gallery shows its photos as a carousel, as the old site did: one large
photo with its caption, arrows (or the arrow keys, or a swipe on a phone) to
move through them, and a strip of thumbnails below. It's switched on by
`carousel: true` in `content/gallery.md`'s header and drawn by
`theme/carousel.js` from the page's photo grid, so the gallery is just the
list of photos in `content/gallery.md`, top first. Without JavaScript the grid
shows instead.

#### Adding news or photos by hand

The *Add news* and *Add photos to the gallery* issues use
`scripts/add-content.py`, which can be run directly too:

```bash
python3 scripts/add-content.py news --month June --year 2025 --text "Colin receives tenure" --link https://…
```

```bash
python3 scripts/add-content.py photos --caption "Lab retreat 2026" ~/Downloads/a.jpg ~/Downloads/b.jpg
```

News goes into `content/news.md` in date order. Photos go at the top of the
gallery, saved in `content/images/gallery/`, turned upright, scaled down to at
most 1600 pixels, and **without their metadata**, so no GPS location is
published. Photos need Pillow (`python3 -m pip install pillow`); the workflow
installs it on GitHub. Both take `--dry-run`. Editing `content/news.md` or
`content/gallery.md` by hand works too; strip a photo's location yourself if
you do.

#### Publishing on GitHub Pages

In Settings > Pages, choose *Deploy from a branch*, branch `main`, folder
`/docs`, and Save. After that, every push publishes the site, first at
`https://blonn25.github.io/kortemmelab.ucsf.edu/`. Every link on the site is
relative, so it works there and at a custom address. Email addresses on
profiles are public, as they were on the old site.

**To use kortemmelab.ucsf.edu:**

1. Ask UCSF IT, who manage `ucsf.edu`, to change the DNS:
   - a **CNAME** record, `kortemmelab.ucsf.edu` → `blonn25.github.io`,
     replacing the one that points at Weebly;
   - a **TXT** record that verifies the domain: in your own GitHub settings >
     Pages > *Add a domain*, enter `kortemmelab.ucsf.edu`, and GitHub shows
     the record to pass on. Verifying stops anyone else from claiming the
     domain on GitHub.
2. Once IT confirms, in the repository's Settings > Pages, enter
   `kortemmelab.ucsf.edu` under **Custom domain** and Save. GitHub adds
   `docs/CNAME` to the repository (the build leaves that file alone); `git
   pull` afterwards. When the DNS check passes, tick **Enforce HTTPS**; the
   certificate can take up to a day.

Don't set the custom domain before the DNS is changed, or GitHub sends
visitors from the github.io address to the old Weebly site. If the repository
is moving to an organization soon, move it first: the CNAME record names the
owner (`<org>.github.io`), so that saves asking IT twice. After the switch,
cancel the Weebly site; old profile addresses keep working through the
forwarding pages.

</details>

<details>
<summary><strong>Where everything is</strong></summary>

#### Layout

```
kortemmelab.ucsf.edu/
├── content/               everything the site says
│   ├── *.md               the 10 pages on the site's menu
│   ├── current-members/   one file per current lab member
│   ├── alumni/            one file per alumnus (including 17 roster-only)
│   ├── images/            every photo the pages use
│   │   ├── people/        every profile's headshot
│   │   └── gallery/       photos added to the gallery since the move
│   ├── bibliography.json  every paper cited on the site, keyed by DOI
│   ├── journal-abbreviations.json   Nature-style journal abbreviations
│   ├── rotation-students.csv   past rotation students, for Lab Alumni
│   └── archive/           old pages kept but not in use (18)
├── theme/                 the look: layout.html, site.css, carousel.js, fonts/
├── scripts/               build-site.py, render-publications.py, bibliography.py,
│                          add-person.py, add-content.py and submission-issue.py
│                          run the site; the rest made the copy of the old site
├── intake/                adding and updating lab members
│   ├── profile-form.html  the form members fill in; saves a .zip
│   ├── github-issue-route.md  joining, updating and leaving through issues; setup
│   ├── form-questions.md  the questions, for a Google or Microsoft form instead
│   ├── profile-template.md   the shape of a profile
│   └── photos/            downloaded headshots go here (kept out of git)
├── docs/                  the website itself, generated: don't edit, rebuild
├── .github/               on GitHub: the issue forms (New lab member, Update my
│                          profile, Add news, Add photos to the gallery), and
│                          workflows that rebuild docs/ after each push
│                          (build-site.yml) and turn those issues into pull
│                          requests (submission.yml)
└── archive/               the old site and how it was copied; for reference only
    ├── site/              the old website; this folder is its web root
    ├── structure/         inventories of the old site (pages, images, papers, emails)
    └── capture/           what was fetched, every file moved, and every
                           original citation
```

Each content file migrated from the old site has YAML frontmatter with the
page title, its old URL, its file in `archive/site/`, and the images and
external links it uses.

#### People are filed by status

The folder a person's file sits in *is* their status, so a graduation done
by hand is a move:

```bash
mv content/current-members/kosuke-seki.md content/alumni/
```

(An *Update my profile* submission with an end year does this for you.)
`content/current-members.md` and `content/lab-alumni.md` are the old roster
pages' text, kept for reference; the site generates both rosters from the two
folders instead.

**Alumni files record their years in the lab** as `years_in_lab` (e.g.
`"2019-2025"`). The old site kept these only on the Lab Alumni roster, and
`scripts/alumni-years.py` copied them to 46 of the 52 migrated alumni. Six
have none: Eleanor Zhu and Rochel Munitz weren't on the roster, and Jenna
Pellegrino, Joel Karpiak, Pooja Suresh and Rocco Varela appeared only among
the rotation students, with the quarter they rotated.

**`content/` is safe to edit by hand.** `extract.py` never overwrites an
existing content file unless you pass `--refresh`, which regenerates files from
`archive/site/` and discards your edits: all of them, or only the pages you
name, as in `--refresh lab-alumni`. It never overwrites a profile.

</details>

<details>
<summary><strong>Publications and the bibliography</strong></summary>

#### How the lists are drawn

Every publication list on the site is drawn from one master list,
`content/bibliography.json`. It holds every paper cited anywhere on the site,
each keyed by its DOI, in CSL-JSON, the standard format that Zotero, Pandoc
and most site generators read. Entries come from each paper's official DOI
record rather than old citation text, so authors, titles and page numbers are
as the publisher registered them. Any entry that was corrected or made by
hand has a `note` saying where its data came from.

- **A person's list** is the DOIs in the `publications:` field at the top of
  their Markdown file, shown newest first.
- **Tanja Kortemme's list is kept complete**: every paper in the bibliography
  with her as an author is added to it automatically.
- **The Publications tab** is every paper in the bibliography with Tanja as an
  author: preprints first, then by year.
- **A preprint is shown only until it's published.** Once a preprint is
  linked to its published version (by its DOI record, by a member's answer in
  the profile form, or by hand), the published paper replaces it on every
  list. A link listed under the preprint's `keep-preprint` doesn't.
- **The style is Nature's, with changes the lab chose.** People's pages list
  every author. The Publications page lists the first five, then "et al."
  (Nature itself keeps only the first). Co-first authors are marked with `*`,
  with a "Co-first authors" note under any list where one shows. Then come the
  title, the journal abbreviated in italics, the volume in bold, the pages or
  article number, and the year. Preprints read "Preprint at *link* (year)."
  Journal abbreviations come from `content/journal-abbreviations.json`.

#### Changing papers by hand

**To add a paper**, put its DOI in the `publications:` list of each lab member
who wrote it (or use `add-person.py --add-papers`; see *Profiles, and changing
people by hand*), then run:

```bash
python3 scripts/render-publications.py
```

It looks the DOI up, adds the paper to the bibliography, and redraws those
people's lists, and Tanja's list and the Publications tab if she's an author.
Lists sit between `publications:start` and `publications:end` markers;
nothing outside them is touched, and anything edited inside them is
overwritten. If a new paper's journal isn't in the abbreviation table, the
script says so. Pushing does all this too, through the rebuild workflow.

**To mark co-first authors** on a paper, add `"co-first": true` to those
authors in its `bibliography.json` entry. They were filled in from the
asterisks in the lab's original citations, for 20 papers.

**To remove a paper**, delete its DOI from the person's list. To take it off
the Publications tab, also delete its entry from `bibliography.json`.

**Preprints:** linking one to its published version by hand is described
under *Reviewing and publishing submissions*, above.

#### Worth knowing

- **Some entries on people's pages are long.** With every author listed, the
  largest consortium papers run to about a hundred names.
- **One paper has no DOI record anywhere**: "SAT-based protein design" (ICCAD
  2009). Its entry was made by hand from the lab's own citation.
- **Titles appear as each publisher registered them**, so some are in Title
  Case.
- When the site moved off Weebly, lab preprints were added to their authors'
  pages, and five were replaced by their published versions.
  `archive/capture/citation-migration.csv` records every original citation, the
  page it was on, and the entry it became; `archive/structure/papers.csv` lists
  every paper and the pages that listed it then (it isn't kept up to date).

</details>

<details>
<summary><strong>Profiles, and changing people by hand</strong></summary>

#### The profile format

Every profile follows `intake/profile-template.md`: `name`, `role`,
`summary`, `photo`, `links`, `education`, `publications` and so on in the
header, and a longer bio as the text below it. Alumni also have
`current_position`, and `position_after_lab` once they've moved on from their
first job. Profiles migrated from the old site keep two more fields,
`source_url` and `mirror_file`, recording which Weebly page they came from;
`build-site.py` uses `mirror_file` to forward the old profile addresses.

Education entries read *Degree, Subject, Institution*: degrees as B.S., B.A.,
M.S., M.Sc. (European master's degrees) and Ph.D., German degrees with the
equivalent in brackets ("Dr. rer. nat. (Ph.D.)"), institutions by their full
names, and a city only for US campuses that give one. `add-person.py` tidies
submissions into this style; a European "Master of Science" written out in
full becomes M.S., so change it to M.Sc. in the pull request.

#### Adding or updating people by hand

The usual routes are the issue forms (see [For lab members](#for-lab-members)).
For someone without a GitHub account, take their `.zip` by email and run:

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip --dry-run
```

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip
```

The same command handles an update `.zip` from the form's *Update my profile*
mode: only the fields the form edits are replaced, and someone given an end
year moves to `content/alumni/`. Every DOI is checked again (any that don't
resolve are left out and reported), and the publication lists are redrawn.
The `.zip` is treated with suspicion: anything in it besides one profile, one
matching photo and the form's small `submission.json` stops it. Several
`.zip` files can go in one command.

To add papers to someone's profile directly:

```bash
python3 scripts/add-person.py --add-papers "Jane Doe" --dois "10.1126/science.abc0881 arXiv:2204.13048"
```

Add `--replace-preprints` if one of the papers is the published version of a
preprint on the website, so the preprint is replaced everywhere it's listed.

Or edit the file yourself: to graduate someone, change `years_in_lab` from
`"2026-present"` to `"2026-2031"`, add `current_position` (and
`position_after_lab`, once they've moved on from their first job), move
their file to `content/alumni/`, and rebuild.

#### From a Google or Microsoft form

If you'd rather collect responses in one place, set up a form with the
questions in `intake/form-questions.md`, keeping the opening words of each
question title, since the script finds answers by them. Export the responses
to `intake/responses.csv`, download the uploaded headshots into
`intake/photos/`, and run:

```bash
python3 scripts/add-person.py --csv intake/responses.csv --dry-run
```

```bash
python3 scripts/add-person.py --csv intake/responses.csv
```

The script reports anything that needs a person's attention: a mistyped
ORCID iD (the check digit catches typos), a DOI that doesn't resolve, an
iPhone HEIC photo (it prints the command to convert it), a photo under 400
pixels, or no photo at all. To add or replace a headshot later:

```bash
python3 scripts/add-person.py --csv intake/responses.csv --only "Jane Doe" --photo ~/Downloads/jane.jpg
```

Someone already in `content/` is skipped, never overwritten. Email addresses
are stored only for people who agreed to show them. The CSV and photos stay
out of git (`intake/.gitignore`). `intake/example-responses.csv` holds two
fictional responses for trying it with `--dry-run`; one uses ORCID's test
researcher, Josiah Carberry (0000-0002-1825-0097), whose iD also works in the
profile form.

#### Notes on the migrated profiles

The 73 profiles migrated from the old site (72 now: a duplicate of Lin Liu's
was deleted) were converted by `scripts/convert-profiles.py` from each
person's old page, its email link, and the alumni roster.
`archive/capture/profile-conversion.csv` lists, for each person, what was
found and anything that needed a look. In short:

- **Most current members have no start year.** The old site never recorded
  one. Fill in `years_in_lab` as `"2021-present"`, or ask them to through
  *Update my profile*.
- **The four alumni listed only under "Staff"** on the old roster (Cristina
  Melero, Debbie Jeon, Florian Lauck, Shane O'Connor) have the role "Staff".
- **Two wrong emails were corrected.** Lisa Schmidt's page linked to Tobias
  Dorer's address and Yulia Gutierrez's to Dru Myerscough's; both pages were
  evidently copied from a colleague's.
- **Names come from each person's own page** where it differs from the old
  page title: Jon Zhang, Anum Azam Glasgow, Yang (Sunny) Zhang.
- **9 have no photo**: five early undergraduates and four rotation students.
- **Fellowships and awards** (e.g. *NSF GRFP Fellow*) are in each bio as they
  were written on the old page.

</details>

<details>
<summary><strong>The old site and its archive</strong></summary>

#### Viewing the old site

`archive/site/` is a copy of the old Weebly site, captured **2026-09-03** and
cleaned up: 100 pages, about 32,500 words, 237 photos, 50 MB. Open
`archive/site/index.html` in a browser, or serve it, which is closer to how a
host would:

```bash
cd archive/site && python3 -m http.server 8899
```

Then visit <http://localhost:8899/>. Everything is local except the live
Google map on Contact and the calendar on Meetings.

#### How the copy differs from the live site

1. **The menu is trimmed.** Research (and its three sub-items), Rosetta and Our
   Wiki are gone, driven by the `HIDE` list in `scripts/customize-nav.py`. The
   pages are still in `archive/site/`, just unlinked.
2. **Tracking and dead code are removed:** Google Analytics, Weebly's
   Snowplow tracker, MathJax (no page contains math), a customer-login system,
   cookie-consent and blog-sharing shims, Weebly's search and commerce
   templates, and Cloudflare's email decoder. Weebly's small `_W.*`
   configuration blocks were kept, since the runtime may read them.
3. **The Contact page's mobile menu works.** On the live site, that page
   carries a calendar script that calls a plugin it never loads, which stops
   jQuery's later page setup, so the phone menu button does nothing. Removing
   the script fixes that; the only visible side effect is a faint 5px footer
   shadow on phones.
4. **The files are reorganized.** Assets wget had nested under their CDN hosts,
   and photos under Weebly's account-sharded folders, are flattened; unused
   Weebly files are pruned (136), fonts are trimmed to `.woff2`, and duplicate
   photos merged. `archive/capture/asset-map.csv` records where every file went.
5. **The HTML is reformatted** with consistent indentation; total HTML went
   from 3.05 MB to 2.10 MB.
6. **Email addresses are readable.** Cloudflare had scrambled 54 `mailto:`
   links; they're decoded, and `archive/structure/emails.csv` lists the 32
   unique ones. They were public on the live site, and with the repository
   public they're public here too.
7. **The gallery is complete.** Weebly builds slideshows from JavaScript, so
   wget never saw the 53 gallery photos; `scripts/fetch-gallery-images.py`
   fetched them.
8. **Broken links are fixed** by `scripts/fix-links.py`: Deniz Akpinaroglu's
   name split across three links (two opening Cody Krivacic's profile), Yulia
   Gutierrez's name linking to a page that no longer exists, and Lisa
   Schmidt's and Yulia's email icons going to colleagues' addresses.
9. **Every publication list is regenerated** from the bibliography in one
   consistent style, replacing four different styles.

#### How the cleanup was checked

Every page was rendered in headless Chrome at desktop width (1280px) and phone
width (390px), before and after the cleanup, and pixel-diffed. **198 of the 202
renders are pixel-identical.** The other four are Contact and Meetings at both
widths, where the differences fall inside the live Google map and calendar
(which also differ between two runs of the untouched site), plus the footer
shadow in point 3. Desktop dropdown menus, the mobile menu and paging through
the gallery were also checked by hand, and every local reference resolves.

#### Archived pages

`content/archive/` holds 18 pages that aren't in use but weren't deleted:

- **The research section** hidden from the menu: `research.md`, the three
  theme pages, and `rosetta.md`. This is the lab's most substantial writing
  outside the people pages.
- **Two drafts**, `incomplete---computational-protein-design-and-modeling.md`
  and `incomplete---evolution-of-structure-function-and-network-interactions.md`.
  Each contains everything in the matching theme page plus one project
  write-up that exists nowhere else, so a rebuilt research section should
  start from these.
- **Eight per-project pages**, each a copy of a section of the theme pages.
  Nothing linked to them, and three are empty on the live site too.
- **Three leftovers.** `internal.md` is a short, unlinked list of lab
  resources. `style-guide.md` is a Weebly template page holding three
  captioned photos, including RosettaCon 2016 and Amanda's third place in the
  2014 Synberc Perfect Pitch contest. `hidden-pages.md` is empty.

**21 of the old site's 100 pages couldn't be reached from its homepage**
(`reachable_from_home` in `archive/structure/pages.csv`), since Weebly keeps
publishing unlinked pages. Most are now in the archive.

#### Known limitations of the copy

- **The Weebly runtime is still in it:** jQuery 1.8.3 plus Weebly's ~480 KB
  `weebly.js`, which its menus and gallery need. The new site uses neither.
- **One link was already broken on the live site** and still is: a "[free
  download]" link in Tanja Kortemme's old publication list with a garbled
  address.
- **Social-preview tags still name the live site**, and external links
  (DOIs, journals, UCSF profiles, the lab's separate `kortemmeweb.ucsf.edu`
  server and wiki) are untouched by design. Server-side features are inert.

#### Capturing it again

This is how `archive/` was made; the website doesn't need it. Re-capture the
live site into an empty `archive/site/` folder:

```bash
curl -s https://kortemmelab.ucsf.edu/sitemap.xml | grep -oE '<loc>[^<]+' | sed 's|<loc>http://|https://|' > archive/capture/sitemap-urls.txt
```

```bash
wget --mirror --page-requisites --convert-links --adjust-extension --span-hosts --domains=kortemmelab.ucsf.edu,cdn11.editmysite.com,cdn2.editmysite.com,cdn.mathjax.org --execute robots=off --wait=0.3 --random-wait --tries=3 --timeout=30 --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" --directory-prefix=archive/site --input-file=archive/capture/sitemap-urls.txt --output-file=archive/capture/wget-mirror.log https://kortemmelab.ucsf.edu/
```

wget exits with status 4 because of a few pages missing upstream; that's
expected. `robots.txt` is ignored, which changes nothing in practice. Then run
the pipeline in order:

```bash
for s in normalize-filenames restructure-root fix-mailto fetch-gallery-images customize-nav tidy-site fix-links extract alumni-years build-bibliography co-first-authors render-publications; do python3 scripts/$s.py || break; done
```

| Script | What it does |
|---|---|
| `normalize-filenames.py` | Strips wget's `?query` suffixes from asset filenames |
| `restructure-root.py` | Flattens wget's one-folder-per-host layout into one web root |
| `fix-mailto.py` | Decodes Cloudflare-scrambled email links |
| `fetch-gallery-images.py` | Fetches the slideshow photos wget can't see |
| `customize-nav.py` | Removes the menu items in its `HIDE` list |
| `tidy-site.py` | Reorganizes files, removes dead code, reformats HTML |
| `fix-links.py` | Fixes the broken links described above |
| `extract.py` | Rebuilds `archive/structure/`; creates any missing `content/` files (`--refresh` rewrites them, but never a profile) |
| `alumni-years.py` | Adds `years_in_lab` to alumni files that don't have it |
| `build-bibliography.py` | Creates `content/bibliography.json` from the original citations. Runs once; never overwrites it |
| `co-first-authors.py` | Marks co-first authors from the asterisks in the original citations |
| `render-publications.py` | Draws every publication list from the bibliography; `--check-preprints` looks for newly published preprints |

`prepare-site-content.py` ran once, moving what the new site needed from the
old pages into `content/`, and `convert-profiles.py` converted the migrated
profiles once; neither has anything left to do. Every script is safe to
re-run and uses only the Python standard library.

</details>
