# kortemmelab.ucsf.edu

The Kortemme Lab website, rebuilt as plain HTML from Markdown files, plus a
copy of the old Weebly site it came from.

- **`docs/`** is the new website, generated from `content/` by
  `scripts/build-site.py`. Open `docs/index.html` to view it. See
  [The website](#the-website) below.
- **`content/`, `theme/`, `scripts/` and `intake/`** are what the website is
  made from (see [Layout](#layout)).
- **`archive/`** holds the copy of the old <https://kortemmelab.ucsf.edu/>,
  captured **2026-09-03**, with the records of how it was made. The new site
  doesn't use anything in it; it's kept for reference.

The old copy, in numbers:

| | |
|---|---|
| Pages | 100 |
| Body text | ~32,500 words |
| Photos | 237 (182 referenced from page text, the rest gallery and click-to-enlarge originals) |
| Size | 50 MB, of which 46 MB is photos |

## The website

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

What the build makes:

| Page | From |
|---|---|
| Home, News, Gallery, Contact, Meetings, Directions, Join the Lab, Publications | `content/<page>.md` |
| Home's Selected Publications and Perspectives and Reviews | the DOIs in `featured_publications` / `featured_reviews` in `content/index.md`'s header |
| Current Members | every file in `content/current-members/`, grouped by `role` |
| Lab Alumni | every file in `content/alumni/`, by role and then newest first, plus `content/rotation-students.csv` |
| `people/<name>.html` | each person's file, unless it says `profile_page: false` (17 older alumni who appear on the roster only) |
| `current---kosuke-seki.html` and the like | small pages forwarding the old site's profile addresses to the new ones |

The look lives in `theme/layout.html` (the frame around every page: header,
menu, footer) and `theme/site.css`. They follow the old theme: Raleway, the
menu centered between thin rules, teal links. Body text is a shade darker than
the old site's for readability. The menu itself is `NAV` near the top of
`build-site.py`. Pages work on phones; the menu folds into a button.

Markdown in `content/` can use headings, paragraphs (a single line break stays
a line break), `-` and `1.` lists, `---` rules, links, images, `**bold**` and
`*italic*`. An image alone in its paragraph becomes a figure, with an
`*italic*` line under it as its caption, and several in a row become a photo
grid. A line of raw HTML passes through as it is, which is how the map and
calendar are embedded.

The Gallery shows its photos as a carousel, as the old site did: one large
photo with its caption, arrows (or the arrow keys, or a swipe on a phone) to
move through them, and a strip of thumbnails below. It's switched on by
`carousel: true` in `content/gallery.md`'s header and drawn by
`theme/carousel.js` from the page's photo grid, so to add a photo, add it to
`content/gallery.md` like the others. Without JavaScript the grid shows
instead.

### Automatic rebuilds

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

### Publishing on GitHub Pages

In the repository's Settings > Pages, choose "Deploy from a branch", branch
`main`, folder `/docs`. After that, every push publishes the site. Two things
to know first:

- **Pages on a private repository needs a paid GitHub plan** (Pro, Team or
  Enterprise). On a free plan the repository would have to be public, and
  `archive/site/` and `archive/structure/emails.csv` hold lab members' email addresses.
- **A published site is public**, even from a private repository. That
  includes the email addresses on profiles, which the old site also showed.

To keep the address kortemmelab.ucsf.edu, add a `docs/CNAME` file containing
it (the build leaves that file alone) and point the domain at GitHub Pages in
UCSF's DNS.

### Viewing the old site

Open `archive/site/index.html` in a browser. Or serve it, which is closer to how a host
would serve it:

```bash
cd archive/site && python3 -m http.server 8899
```

Then visit <http://localhost:8899/>. Everything is local except two live
Google embeds that need an internet connection: the map on the Contact page and
the calendar on Meetings. (The new site has the same two; its map is a plain
Google Maps embed, since the old one went through Weebly.)

## Layout

```
kortemmelab.ucsf.edu/
├── content/               everything the site says
│   ├── *.md               the 10 pages on the site's menu
│   ├── current-members/   one file per current lab member (20)
│   ├── alumni/            one file per alumnus (52, plus 17 roster-only)
│   ├── images/            every photo the pages use
│   │   └── people/        every profile's headshot
│   ├── bibliography.json  every paper cited on the site, keyed by DOI (see below)
│   ├── journal-abbreviations.json   Nature-style journal abbreviations
│   ├── rotation-students.csv   past rotation students, for Lab Alumni
│   └── archive/           old pages kept but not in use (18), see below
├── theme/                 the look: layout.html, site.css, carousel.js, fonts/
├── scripts/               build-site.py, render-publications.py, bibliography.py,
│                          add-person.py and profile-issue.py run the site;
│                          the rest made the copy of the old site (see Regenerating)
├── intake/                adding new lab members (see below)
│   ├── profile-form.html  the form new members fill in; saves a .zip
│   ├── github-issue-route.md  joining, updating and leaving through issues; setup
│   ├── form-questions.md  the questions, for a Google or Microsoft form instead
│   ├── profile-template.md   the shape of a new member's profile
│   └── photos/            downloaded headshots go here (kept out of git)
├── docs/                  the website itself, generated: don't edit, rebuild
├── .github/               on GitHub: the New lab member and Update my profile issue
│                          forms, and workflows that rebuild docs/ after each push
│                          (build-site.yml) and turn those issues into pull requests
│                          (profile-submission.yml)
└── archive/               the old site and how it was copied; for reference only
    ├── site/              the old website; this folder is its web root
    │   ├── *.html         100 pages, same filenames as the live site
    │   ├── images/        every photo, flat
    │   └── assets/        Weebly's CSS and JavaScript, Raleway, theme images
    ├── structure/         inventories of the old site
    │   ├── site-structure.json   navigation tree and per-page metadata
    │   ├── pages.csv             one row per page: title, word count, reachability
    │   ├── images.csv            every image a page uses, with its local path
    │   ├── papers.csv            every paper, with the pages that listed it
    │   └── emails.csv            contact addresses, per page
    └── capture/           what was fetched, every file moved, and every
                           original citation
```

Each content file has YAML frontmatter with the page title, its live URL, its
file in `archive/site/`, word count, whether it's reachable from the homepage, and the
images and external links it uses.

**People are filed by status.** The folder a person's file sits in *is* their
status, so when someone graduates, move their file:

```bash
mv content/current-members/kosuke-seki.md content/alumni/
```

Any file in `content/` stays wherever you put it. The live site's `current---`/`alumni---` prefixes only decide where
a person goes the first time their file is created. `content/current-members.md`
and `content/lab-alumni.md` are the old roster pages' text, kept for reference;
the new site generates both rosters from the two folders instead.

**Alumni files record their years in the lab** as `years_in_lab` in the
frontmatter (e.g. `"2019-2025"`). The live site kept these only on the Lab
Alumni roster, and `scripts/alumni-years.py` copied them to 46 of the 52
alumni. When someone graduates, add the field yourself. The script only fills
it in where it's missing, so it never overwrites yours. The other six have
no years on the roster: Eleanor Zhu and Rochel Munitz aren't on it at all,
and Jenna Pellegrino, Joel Karpiak, Pooja
Suresh and Rocco Varela appear only in its list of rotation students, with the
quarter they rotated rather than their years in the lab.

**`content/` is safe to edit by hand.** `extract.py` never overwrites an
existing content file unless you pass `--refresh`, which regenerates files from
`archive/site/` and discards your edits: all of them, or only the pages you name, as
in `--refresh lab-alumni`.

## Publications

Every publication list on the site is drawn from one master list,
`content/bibliography.json`. It holds every paper cited anywhere on the site,
253 entries, each keyed by its DOI, in CSL-JSON, the standard format that
Zotero, Pandoc and most site generators read. Entries come from each paper's
official DOI record rather than the old citation text, so authors, titles and
page numbers are as the publisher registered them. Any entry that was
corrected or made by hand has a `note` saying where its data came from.

- **A person's list** is the DOIs in the `publications:` field at the top of
  their Markdown file, shown newest first.
- **Tanja Kortemme's list is kept complete**: every paper in the bibliography
  with her as an author is added to it automatically.
- **The Publications tab** is every paper in the bibliography with Tanja as an
  author (117 now): preprints first, then by year.
- **A preprint is shown only until it's published.** Once a preprint's DOI
  record names its published version, the published paper replaces it on
  every person's list and on the Publications tab. The record is checked when
  you run the script with `--check-preprints`.
- **The style is Nature's, with changes the lab chose.** People's pages list
  every author. The Publications page lists the first five, then "et al."
  (Nature itself keeps only the first). Co-first authors are marked with `*`,
  with a "Co-first authors" note under any list where one shows. Then come the title,
  the journal abbreviated in italics, the volume in bold, the pages or article
  number, and the year. Preprints read "Preprint at *link* (year)." Journal
  abbreviations come from `content/journal-abbreviations.json`.

**To add a paper**, put its DOI in the `publications:` list of each lab member
who wrote it, then run:

```bash
python3 scripts/render-publications.py
```

It looks the DOI up, adds the paper to the bibliography, and redraws those
people's lists, and Tanja's list and the Publications tab if she's an author,
in `content/`; then rebuild the site. Lists sit between `publications:start` and
`publications:end` markers; nothing outside them is touched, and anything
edited inside them is overwritten. If a new paper's journal isn't in the
abbreviation table, the script says so.

**To mark co-first authors** on a paper, add `"co-first": true` to those
authors in its `bibliography.json` entry. They were filled in from the
asterisks in the lab's original citations, for 20 papers.

**To remove a paper**, delete its DOI from the person's list. To take it off
the Publications tab, also delete its entry from `bibliography.json`.

Worth knowing:

- **Lab preprints were added to their authors' pages.** Amy Guo, Benjamin Orr,
  Deniz Akpinaroglu, Eleanor Zhu, Alex Li, Kosuke Seki and Stephanie Crilly
  gained 12 between them. Benjamin's and Eleanor's profiles had an empty
  "Publications" heading, so their lists went under it.
- **Five preprints were replaced by their published versions**: Deniz
  Akpinaroglu's antibody and polarity papers, Kevin Alexander Estrada Alamo's
  integrin paper, Radhika Dalal's 3D protein crystals paper, and Tina Perica's
  GTPase paper. The preprints stay in the bibliography to record the link.
- **Some entries on people's pages are long.** With every author listed, the
  largest consortium papers run to about a hundred names.
- **One paper has no DOI record anywhere**: "SAT-based protein design" (ICCAD
  2009). Its entry was made by hand from the lab's own citation.
- **Titles appear as each publisher registered them**, so some are in Title
  Case.
- `archive/capture/citation-migration.csv` records every original citation, the page it
  was on, and the entry it became. `archive/structure/papers.csv` lists every paper and
  the pages that listed it when the site moved off Weebly (it isn't kept up
  to date).

## Adding a new lab member

**The usual way: the profile form and a GitHub issue.** New members open
Issues > New issue > **New lab member**. That issue form links to the profile
form (`intake/profile-form.html`, also published as `profile-form.html` on
the website, on no menu). The profile form opens in any browser and needs
nothing installed. They fill in their details, pick their papers
from their ORCID record or type DOIs (each is looked up as they go), add a
headshot, check the preview, and click Save. That gives them one file,
`<first-last>-profile.zip`, which they attach to the issue. A workflow checks
it, replies on the issue, and opens a pull request adding them; you merge it,
and the site rebuilds. Setup (two settings) and the details are in
`intake/github-issue-route.md`.

Nothing they type leaves their computer except the ORCID iD and DOIs, which
the page looks up at orcid.org and doi.org. Their answers are kept in their
browser until they save, so they can stop and come back. Photos are scaled
down to at most 1000 pixels, so the `.zip` stays small.

Anyone without a GitHub account can email you the `.zip` instead. Add them
yourself with:

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip --dry-run
```

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile.zip
```

This files their profile in `content/current-members/` and their headshot in
`content/images/people/`, checks every DOI again (any that don't resolve are
left out and reported), and draws their publication list. The `.zip` is
treated with suspicion: anything in it besides one profile and one matching
photo stops it. Several `.zip` files can go in one command.

**Or a Google or Microsoft form**, if you'd rather collect responses in one
place. Set one up with the questions in `intake/form-questions.md`, keeping
the opening words of each question title, since the script finds answers by
them. Export the responses to `intake/responses.csv`, download the uploaded
headshots into `intake/photos/`, and run:

```bash
python3 scripts/add-person.py --csv intake/responses.csv --dry-run
```

```bash
python3 scripts/add-person.py --csv intake/responses.csv
```

Either way, each new member gets `content/current-members/<first-last>.md`,
following `intake/profile-template.md`, and their publication list is drawn.
Publications come from their ORCID iD, from DOIs or arXiv IDs, or both, so
people without an ORCID can still list their papers.

From a CSV, the script reports anything that needs a person's attention: a
mistyped ORCID iD (the check digit catches typos), a DOI that doesn't resolve,
an iPhone HEIC photo (it prints the command to convert it), a photo under 400
pixels, or no photo at all. The profile form catches the same things while
the person is still filling it in. To add or replace a headshot later:

```bash
python3 scripts/add-person.py --csv intake/responses.csv --only "Jane Doe" --photo ~/Downloads/jane.jpg
```

Someone already in `content/` is skipped, never overwritten: changes to an
existing profile come through *Update my profile* (below), or by editing the
file directly. Email addresses are stored only for people who agreed to show them.
`intake/example-responses.csv` holds two fictional responses for trying the
CSV route with `--dry-run`. One uses ORCID's own test researcher, Josiah
Carberry, whose iD (0000-0002-1825-0097) also works in the profile form.

Then rebuild the site (`python3 scripts/build-site.py`) and push, or just
push: GitHub rebuilds it (below).

### Updating a profile, and leaving the lab

Current members and alumni open an **Update my profile** issue. To add new
papers, they just type their name and the DOIs. For anything else, they load
their current profile into the profile form (in its *Update my profile*
mode), change it, and attach the `.zip`. The form's **I've left the lab, or
I'm leaving it** option takes the year and what they're doing next, and the
pull request moves them to Lab Alumni. A workflow opens the pull request;
you merge it. How it works, the identity check, and setup are in
`intake/github-issue-route.md`.

The same can be done by hand:

```bash
python3 scripts/add-person.py --zip ~/Downloads/jane-doe-profile-update.zip
```

```bash
python3 scripts/add-person.py --add-papers "Jane Doe" --dois "10.1126/science.abc0881 arXiv:2204.13048"
```

An update replaces only the fields the form edits and keeps everything else
in the file. Or edit the file yourself: to graduate someone, change
`years_in_lab` from `"2026-present"` to `"2026-2031"`, add `current_position`
(and `position_after_lab`, once they've moved on from their first job), move
their file to `content/alumni/`, and rebuild.

**Planned, once the repository moves to a GitHub organization:** Read-only
access for members, publishing on GitHub Pages, and a "Find me" list in the
profile form instead of downloading your profile file. See the end of
`intake/github-issue-route.md`.

## Profiles

Every profile, new or migrated, follows `intake/profile-template.md`: `name`,
`role`, `summary`, `photo`, `links`, `education`, `publications` and so on in
the header, and a longer bio as the text below it. Alumni also have
`current_position`. Profiles migrated from the old site keep two more fields,
`source_url` and `mirror_file`, recording which Weebly page they came from;
the renderer uses `mirror_file` to keep the local copy of the old site in
step. Profiles are edited by hand: `extract.py` never overwrites one, even
with `--refresh`.

The 73 migrated profiles (72 now: a duplicate of Lin Liu's was deleted) were
converted by `scripts/convert-profiles.py`
from three sources: the text of each person's old page, its email link, and
the alumni roster. The roster supplied photos, roles and current positions
for the 38 older alumni whose own pages held only a publication list.
`archive/capture/profile-conversion.csv` lists, for each person, what was found and
anything that needs a look. In short:

- **20 current members have no start year.** The old site never recorded
  one. Fill in `years_in_lab` as `"2021-present"`.
- **Every profile has a role.** The roster supplied them for older alumni;
  the four it lists only under "Staff" (Cristina Melero, Debbie Jeon, Florian
  Lauck, Shane O'Connor) have "Staff", and five that the old pages left out
  were filled in by hand.
- **Two wrong emails were corrected.** Lisa Schmidt's page linked to Tobias
  Dorer's address and Yulia Gutierrez's to Dru Myerscough's; both pages were
  evidently copied from a colleague's. Their profiles now have their own
  addresses, and `scripts/fix-links.py` corrects the email links on their
  pages in `archive/site/` too.
- **Names come from each person's own page** where it differs from the old
  page title: Jon Zhang, Anum Azam Glasgow, Yang (Sunny) Zhang.
- **9 have no photo**: five early undergraduates and four rotation students.
  The roster had no photo for any of them.
- **Fellowships and awards** (e.g. *NSF GRFP Fellow*) are in each bio as they
  were written on the old page.

## How it differs from the live site

1. **The menu is trimmed.** Research (and its three sub-items), Rosetta and Our
   Wiki are gone, leaving Home / People / Publications / News / Gallery /
   Contact. That's driven by the `HIDE` list in `scripts/customize-nav.py`. The
   pages themselves are still in `archive/site/`, just unlinked. To delete them:

   ```bash
   cd site && rm research.html rosetta.html computational-protein-design-and-modeling.html control-of-biological-systems.html evolution-of-structure-function-and-network-interactions.html
   ```

2. **Tracking and dead code are removed.** Every page used to load Google
   Analytics and Weebly's Snowplow tracker, so viewing the *local* copy reported
   to the lab's analytics. Both are gone, along with MathJax (no page contains
   math), a customer-login system, cookie-consent shims, a blog-sharing shim,
   Weebly's search and commerce templates, and Cloudflare's email decoder.
   Weebly's small `_W.*` configuration blocks were kept on purpose, since the
   runtime may read them in states a test can't reach.

3. **The Contact page's mobile menu works.** On the live site, that page
   carries a calendar script that calls a plugin it never loads. The error it
   throws stops jQuery from running any later page setup, so on phones the
   menu button on Contact does nothing. Removing the script fixes that. This is
   the one deliberate visual difference: on phone-width screens, a faint 5px
   shadow under that page's footer area disappears, because the theme's setup
   code now runs there the way it does on every other page.

4. **The files are reorganized.** wget had left assets nested under the CDN
   hosts they came from (up to
   `_cdn/cdn11.editmysite.com/images/common/checkmarks/@2x/`), and photos under
   Weebly's account-sharded `uploads/7/2/7/7/72776173/published/`. Weebly
   platform files are now pruned to the ones some page actually uses (136 files
   removed), fonts are trimmed to `.woff2`, the format every current browser
   uses, and byte-identical duplicate photos are merged. `archive/capture/asset-map.csv`
   records where every file went.

5. **The HTML is reformatted** with consistent two-space indentation, one tag
   per line in `<head>`, collapsed multi-line tags, and redundant attributes
   removed. The contact page went from 682 lines to 292, and total HTML from
   3.05 MB to 2.10 MB. No CSS on the site uses `white-space: pre`, so collapsing
   whitespace runs can't change what renders.

6. **Email addresses are readable.** Cloudflare had scrambled 54 `mailto:` links
   into dead `/cdn-cgi/…` URLs. They're decoded back to plain addresses, and
   `archive/structure/emails.csv` lists the 32 unique ones, mostly lab members'
   personal addresses. They were public on the live site only behind
   Cloudflare's anti-scraper obfuscation, so **re-apply equivalent protection
   if you republish them**, and keep any repository holding this folder private.

7. **The gallery is complete.** Weebly builds slideshows from JavaScript rather
   than `<img>` tags, so wget never saw the 53 gallery photos.
   `scripts/fetch-gallery-images.py` fetched them, at display size and as
   full-resolution `_orig` files. The gallery also works when a page is opened
   straight from disk now, not just from a server.

8. **Broken links are fixed**, by `scripts/fix-links.py`. On the alumni
   roster, Deniz Akpinaroglu's name was split across three links, and "Deni"
   and "z" opened Cody Krivacic's profile. It's now one link, bold like every
   other name. On Yulia Gutierrez's profile, her own name linked to Deniz's
   old current-member page, which no longer exists. It's now plain text, like
   the name at the top of every other profile.
   Lisa Schmidt's and Yulia Gutierrez's email icons went to colleagues'
   addresses, Tobias Dorer's and Dru Myerscough's, and Lisa's name linked to
   Tobias's profile; all three now point where they should.

9. **Every publication list is regenerated** from the bibliography in one
   consistent style, replacing four different styles. The Publications
   page now runs by year from 2025 back to 1993; its earliest work was grouped
   by topic before.

## How the cleanup was verified to change nothing visible

Every page was rendered in headless Chrome at desktop width (1280px) and phone
width (390px), before and after the cleanup, and pixel-diffed. **198 of the 202
renders are pixel-identical.** The other four are Contact and Meetings at both
widths. Their differences fall inside the live Google map and calendar, which
also differ between two runs of the untouched site. The one exception is the
footer shadow described in point 3.

Static renders can't catch everything, so these interactions were also checked:
desktop dropdown menus, the mobile menu and its sub-menu expanders, and paging
through the gallery. That's how the cleanup knows to keep Raleway *regular*,
which only loads when you hover the menu, and the gallery's full-size photos,
which only load when you click "next". Every local reference in every page and
stylesheet resolves.

## The archive

`content/archive/` holds 18 pages that aren't in use but weren't deleted:

- **The research section** you hid from the menu: `research.md`, the three
  theme pages, and `rosetta.md`. This is the lab's most substantial writing
  outside the people pages.
- **Two drafts**, `incomplete---computational-protein-design-and-modeling.md`
  and `incomplete---evolution-of-structure-function-and-network-interactions.md`.
  Each contains everything in the matching theme page plus one project
  write-up that exists nowhere else, so a rebuilt research section should
  start from these rather than from the live versions.
- **Eight per-project pages**, each a copy of a section of the theme pages.
  Nothing linked to them, and three are empty on the live site too.
- **Three leftovers.** `internal.md` is a short, unlinked list of lab
  resources. `style-guide.md` is a Weebly template page, but it holds three
  captioned photos, including RosettaCon 2016 and Amanda's third place in the
  2014 Synberc Perfect Pitch contest. `hidden-pages.md` is empty.

## Pages no visitor can reach

**21 of the 100 pages can't be reached by clicking from the homepage.** The
`reachable_from_home` column in `archive/structure/pages.csv` flags them. Weebly keeps
publishing a page after it's unlinked, so the sitemap lists pages no visitor
can find. Most are now in the archive. The ones that matter are people:
`current---lisa-schmidt.html` is a *current* member whose page is missing
from Current Members, which is probably an oversight; and
`alumni---eleanor-zhu.html` and `alumni---rochel-munitz.html` are unlinked
too.

Also note that 72 of the 100 pages are individual profiles (20 current
members, 52 alumni), which is worth knowing before choosing a template.

## Known limitations

- **The Weebly runtime is still here.** That's jQuery 1.8.3 (from 2012) plus
  Weebly's ~480 KB `weebly.js`, which this theme needs for its menus and
  gallery. A rebuild would replace it rather than keep it.
- **One link was already broken on the live site** and still is: a
  "[free download]" link in Tanja Kortemme's publication list whose address is
  garbled (`/%3Ca%20class=`), so its real target can't be recovered.
- **Social-preview tags (`og:image`, `og:url`) still name the live site.** By
  spec they must be absolute URLs, and browsers never fetch them.
- **External links are untouched by design.** That covers DOIs, journals, UCSF
  profiles, and `kortemmeweb.ucsf.edu`, the lab's separate Backrub server and
  wiki, which wasn't captured.
- **Server-side features are inert**, as on any static copy.

## Regenerating

This is how `archive/` was made. The website doesn't need it: it's only for
re-copying the old Weebly site, should that ever be wanted. Re-capture the
live site into an empty `archive/site/` folder:

```bash
curl -s https://kortemmelab.ucsf.edu/sitemap.xml | grep -oE '<loc>[^<]+' | sed 's|<loc>http://|https://|' > archive/capture/sitemap-urls.txt
```

```bash
wget --mirror --page-requisites --convert-links --adjust-extension --span-hosts --domains=kortemmelab.ucsf.edu,cdn11.editmysite.com,cdn2.editmysite.com,cdn.mathjax.org --execute robots=off --wait=0.3 --random-wait --tries=3 --timeout=30 --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" --directory-prefix=archive/site --input-file=archive/capture/sitemap-urls.txt --output-file=archive/capture/wget-mirror.log https://kortemmelab.ucsf.edu/
```

wget exits with status 4 because of the upstream 404s above. That's expected.
`robots.txt` is ignored, which changes nothing in practice: the one page it
disallows no longer exists. Then run the pipeline in order:

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

Two more scripts make the new site from that:

| Script | What it does |
|---|---|
| `prepare-site-content.py` | Ran once: moved what the new site needed from the old pages into `content/` (roster-only alumni, rotation students, Home's featured papers, the map and calendar, News as dated items) |
| `build-site.py` | Builds `docs/` from `content/` (see [The website](#the-website)) |

`bibliography.py` holds the parts the publication scripts share, including the Nature-style
formatter. `convert-profiles.py` converted the migrated profiles once and has
nothing left to do. `add-person.py` isn't part of this pipeline; it's for adding new
lab members (above).

Every script is safe to re-run; on a finished site, all but `extract.py` report
nothing to do. They use only the Python standard library.
