# kortemmelab.ucsf.edu — local copy

A local copy of <https://kortemmelab.ucsf.edu/>, captured **2026-09-03** from
the lab's Weebly site. It's cleaned up into a conventional static-site layout,
and the page text is extracted to serve as a starting point for a rebuild.

| | |
|---|---|
| Pages | 100 |
| Body text | ~32,500 words |
| Photos | 237 (182 referenced from page text, the rest gallery and click-to-enlarge originals) |
| Size | 50 MB, of which 46 MB is photos |

## Viewing it

Open `site/index.html` in a browser. Or serve it, which is closer to how a host
would serve it:

```bash
cd site && python3 -m http.server 8899
```

Then visit <http://localhost:8899/>. Everything is local except two live
Google embeds that need an internet connection: the map on the Contact page and
the calendar on Meetings.

## Layout

```
kortemmelab.ucsf.edu/
├── site/                  the website; this folder is the web root
│   ├── *.html             100 pages, same filenames as the live site
│   ├── images/            every photo, flat
│   │   └── backgrounds/   page background images
│   └── assets/
│       ├── css/           weebly.css (platform base), theme.css (the site's
│       │                  own theme), Raleway, slideshow, social icons
│       ├── js/            jQuery 1.8.3, the Weebly runtime, slideshow, theme
│       ├── fonts/         Raleway in six weights, and the social-icon font
│       └── img/           theme and interface images
├── content/               one Markdown file per page: the text, for a rebuild
│   ├── bibliography.json  every paper cited on the site, keyed by DOI (see below)
│   ├── journal-abbreviations.json   Nature-style journal abbreviations
│   ├── *.md               the 10 pages on the site's menu
│   ├── current-members/   one file per current lab member (20)
│   ├── alumni/            one file per alumnus (52)
│   ├── images/people/     every profile's headshot
│   └── archive/           pages kept but not in use (18), see below
├── structure/             inventories for a rebuild
│   ├── site-structure.json   navigation tree and per-page metadata
│   ├── pages.csv             one row per page: title, word count, reachability
│   ├── images.csv            every image a page uses, with its local path
│   ├── papers.csv            every paper, with the pages that list it
│   └── emails.csv            contact addresses, per page
├── intake/                adding new lab members (see below)
│   ├── form-questions.md  the questions for the intake form
│   ├── profile-template.md   the shape of a new member's profile
│   └── photos/            downloaded headshots go here (kept out of git)
├── scripts/               the pipeline that produced all of the above
└── capture/               provenance: what was fetched, every file moved,
                           and every original citation
```

Each content file has YAML frontmatter with the page title, its live URL, its
file in `site/`, word count, whether it's reachable from the homepage, and the
images and external links it uses.

**People are filed by status.** The folder a person's file sits in *is* their
status, so when someone graduates, move their file:

```bash
mv content/current-members/kosuke-seki.md content/alumni/
```

Any file in `content/` stays wherever you put it, and `structure/pages.csv`
follows it. The live site's `current---`/`alumni---` prefixes only decide where
a person goes the first time their file is created. `content/current-members.md`
and `content/lab-alumni.md` are the old roster pages' text, and still list
people by name; a rebuild should generate rosters from the two folders instead.

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
`site/` and discards your edits: all of them, or only the pages you name, as
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
in both `site/` and `content/`. Lists sit between `publications:start` and
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
- `capture/citation-migration.csv` records every original citation, the page it
  was on, and the entry it became. `structure/papers.csv` lists every paper and
  the pages that list it.

## Adding a new lab member

New members fill in a short form; one command turns the responses into
profiles.

1. **Set up the form once**, in Google Forms or Microsoft Forms, using the
   questions in `intake/form-questions.md`. Keep the opening words of each
   question title; the script finds answers by them.
2. **When people have responded**, export the responses as a CSV to
   `intake/responses.csv`, and download the uploaded headshots into
   `intake/photos/`.
3. **Preview, then add:**

   ```bash
   python3 scripts/add-person.py --csv intake/responses.csv --dry-run
   ```

   ```bash
   python3 scripts/add-person.py --csv intake/responses.csv
   ```

Each new member gets `content/current-members/<first-last>.md`, following
`intake/profile-template.md`. Their headshot is copied to
`content/images/people/`, and their publication list is drawn. Publications
come from their ORCID iD, from DOIs or arXiv IDs typed into the form, or both,
so people without an ORCID can still list their papers. Every DOI is checked
first; any that don't resolve are reported and left out.

The script reports anything that needs a person's attention: a mistyped
ORCID iD (the check digit catches typos), a DOI that doesn't resolve, an
iPhone HEIC photo (it prints the command to convert it), a photo under 400
pixels, or no photo at all. To add or replace a headshot later:

```bash
python3 scripts/add-person.py --csv intake/responses.csv --only "Jane Doe" --photo ~/Downloads/jane.jpg
```

Someone already in `content/` is skipped, never overwritten; edit their file
directly. Email addresses are stored only for people who agreed to show them.
`intake/example-responses.csv` holds two fictional responses for trying the
script with `--dry-run`. One uses ORCID's own test researcher, Josiah
Carberry.

**When someone graduates**, change `years_in_lab` from `"2026-present"` to
the end year (`"2026-2031"`) and move their file to `content/alumni/`.

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
`capture/profile-conversion.csv` lists, for each person, what was found and
anything that needs a look. In short:

- **20 current members have no start year.** The old site never recorded
  one. Fill in `years_in_lab` as `"2021-present"`.
- **4 have no role**: alumni listed under "Staff" on the roster without a
  title (Cristina Melero, Debbie Jeon, Florian Lauck, Shane O'Connor). Roles
  for the other five the old pages left out were filled in by hand.
- **Two wrong emails were corrected.** Lisa Schmidt's page linked to Tobias
  Dorer's address and Yulia Gutierrez's to Dru Myerscough's; both pages were
  evidently copied from a colleague's. Their profiles now have their own
  addresses. The old pages, and so the local copy in `site/`, still have the
  wrong links.
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
   pages themselves are still in `site/`, just unlinked. To delete them:

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
   uses, and byte-identical duplicate photos are merged. `capture/asset-map.csv`
   records where every file went.

5. **The HTML is reformatted** with consistent two-space indentation, one tag
   per line in `<head>`, collapsed multi-line tags, and redundant attributes
   removed. The contact page went from 682 lines to 292, and total HTML from
   3.05 MB to 2.10 MB. No CSS on the site uses `white-space: pre`, so collapsing
   whitespace runs can't change what renders.

6. **Email addresses are readable.** Cloudflare had scrambled 54 `mailto:` links
   into dead `/cdn-cgi/…` URLs. They're decoded back to plain addresses, and
   `structure/emails.csv` lists the 32 unique ones, mostly lab members'
   personal addresses. They were public on the live site only behind
   Cloudflare's anti-scraper obfuscation, so **re-apply equivalent protection
   if you republish them**, and keep any repository holding this folder private.

7. **The gallery is complete.** Weebly builds slideshows from JavaScript rather
   than `<img>` tags, so wget never saw the 53 gallery photos.
   `scripts/fetch-gallery-images.py` fetched them, at display size and as
   full-resolution `_orig` files. The gallery also works when a page is opened
   straight from disk now, not just from a server.

8. **Two broken links are fixed**, by `scripts/fix-links.py`. On the alumni
   roster, Deniz Akpinaroglu's name was split across three links, and "Deni"
   and "z" opened Cody Krivacic's profile. It's now one link, bold like every
   other name. On Yulia Gutierrez's profile, her own name linked to Deniz's
   old current-member page, which no longer exists. It's now plain text, like
   the name at the top of every other profile.

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
`reachable_from_home` column in `structure/pages.csv` flags them. Weebly keeps
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

Re-capture the live site into an empty `site/` folder:

```bash
curl -s https://kortemmelab.ucsf.edu/sitemap.xml | grep -oE '<loc>[^<]+' | sed 's|<loc>http://|https://|' > capture/sitemap-urls.txt
```

```bash
wget --mirror --page-requisites --convert-links --adjust-extension --span-hosts --domains=kortemmelab.ucsf.edu,cdn11.editmysite.com,cdn2.editmysite.com,cdn.mathjax.org --execute robots=off --wait=0.3 --random-wait --tries=3 --timeout=30 --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" --directory-prefix=site --input-file=capture/sitemap-urls.txt --output-file=capture/wget-mirror.log https://kortemmelab.ucsf.edu/
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
| `fix-links.py` | Fixes the two broken links described above |
| `extract.py` | Rebuilds `structure/`; creates any missing `content/` files (`--refresh` rewrites them, but never a profile) |
| `alumni-years.py` | Adds `years_in_lab` to alumni files that don't have it |
| `build-bibliography.py` | Creates `content/bibliography.json` from the original citations. Runs once; never overwrites it |
| `co-first-authors.py` | Marks co-first authors from the asterisks in the original citations |
| `render-publications.py` | Draws every publication list from the bibliography; `--check-preprints` looks for newly published preprints |

`bibliography.py` holds the parts those two share, including the Nature-style
formatter. `convert-profiles.py` converted the migrated profiles once and has
nothing left to do. `add-person.py` isn't part of this pipeline; it's for adding new
lab members (above).

Every script is safe to re-run; on a finished site, all but `extract.py` report
nothing to do. They use only the Python standard library.
