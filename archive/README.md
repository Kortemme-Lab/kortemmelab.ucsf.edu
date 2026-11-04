# The old site and how it was moved

The Kortemme Lab website used to run on Weebly. This folder keeps a cleaned-up
copy of that site and the record of how its content moved into `content/`.
**The website doesn't use anything here**; it's for reference.

- `site/`: the old website; this folder is its web root
- `structure/`: inventories of the old site (pages, images, papers, emails)
- `capture/`: what was fetched, where every file moved, and every original
  citation

## Viewing the old site

`site/` was captured **2026-09-03**: 100 pages, about 32,500 words, 237
photos, 50 MB. Open `archive/site/index.html` in a browser, or serve it:

```bash
cd archive/site && python3 -m http.server 8899
```

Then visit <http://localhost:8899/>. Everything is local except the live
Google map on Contact and the calendar on Meetings.

## How the copy differs from the live site

1. **The menu is trimmed.** Research (and its three sub-items), Rosetta and
   Our Wiki are unlinked (the `HIDE` list in `scripts/customize-nav.py`); the
   pages are still there.
2. **Tracking and dead code are removed:** Google Analytics, Weebly's
   Snowplow tracker, MathJax, a customer-login system, cookie-consent and
   blog-sharing shims, Weebly's search and commerce templates, and
   Cloudflare's email decoder.
3. **The Contact page's phone menu works.** On the live site a calendar script
   calls a plugin it never loads, which stops the menu button working.
4. **The files are reorganized:** CDN folders flattened, 136 unused Weebly
   files pruned, fonts trimmed to `.woff2`, duplicate photos merged.
   `capture/asset-map.csv` records where every file went.
5. **The HTML is reformatted** (3.05 MB down to 2.10 MB).
6. **Email addresses are readable.** Cloudflare had scrambled 54 `mailto:`
   links; `structure/emails.csv` lists the 32 unique ones. They were public on
   the live site, and are public here too.
7. **The gallery is complete.** wget can't see Weebly's slideshow photos, so
   `scripts/fetch-gallery-images.py` fetched the 53 of them.
8. **Broken links are fixed** by `scripts/fix-links.py` (Deniz Akpinaroglu's
   split name, Yulia Gutierrez's dead link, and two email icons pointing at
   colleagues).
9. **Every publication list is regenerated** from the bibliography in one
   style, replacing four.

**How it was checked:** every page was rendered in headless Chrome at 1280px
and 390px, before and after, and pixel-diffed. 198 of 202 renders are
identical; the rest differ only inside the live map and calendar, plus a
faint footer shadow from point 3.

**Known limitations:** the Weebly runtime (jQuery 1.8.3 and ~480 KB of
`weebly.js`) is still in the copy, since its menus and gallery need it. One
link was already broken on the live site (a garbled "[free download]" in
Tanja's old publication list). Social-preview tags still name the live site,
and external links are untouched by design.

## Archived pages

`content/archive/` holds 18 old pages that aren't in use:

- **The research section** hidden from the menu: `research.md`, the three
  theme pages, and `rosetta.md`, the lab's most substantial writing outside
  the people pages.
- **Two drafts** (`incomplete---…`), each holding a matching theme page plus
  one project write-up found nowhere else: start here to rebuild a research
  section.
- **Eight per-project pages**, copies of sections of the theme pages.
- **Three leftovers:** `internal.md` (lab resources), `style-guide.md` (three
  captioned photos, including RosettaCon 2016) and an empty `hidden-pages.md`.

21 of the old site's 100 pages weren't reachable from its homepage
(`reachable_from_home` in `structure/pages.csv`).

## How the content was moved

- `scripts/extract.py` made the files in `content/` from `site/`. It never
  overwrites an existing file unless given `--refresh` (all pages, or only
  those named, e.g. `--refresh lab-alumni`), and never a profile.
- `scripts/prepare-site-content.py` moved what the new site needed into
  `content/`, once.
- Each migrated content file's header records its title, old URL, file in
  `site/`, and the images and links it uses.
- **Publications:** `scripts/build-bibliography.py` made
  `content/bibliography.json` from the original citations, once, from each
  paper's DOI record. `scripts/co-first-authors.py` marked co-first authors
  from the asterisks in them (20 papers). Lab preprints were added to their
  authors' pages, and five replaced by their published versions.
  `capture/citation-migration.csv` records every original citation, its page
  and the entry it became; `structure/papers.csv` lists every paper and the
  pages that listed it then (not kept up to date).

### The migrated profiles

`scripts/convert-profiles.py` converted 73 profiles (72 now: a duplicate of
Lin Liu's was deleted) from each person's old page, its email link and the
alumni roster. `capture/profile-conversion.csv` lists what was found for each
and anything that needed a look. In short:

- **Most current members have no start year;** the old site never recorded
  one. They can add it through *Update my profile*.
- **Alumni years** came from the old roster (`scripts/alumni-years.py`), for
  46 of 52. Eleanor Zhu and Rochel Munitz weren't on it; Jenna Pellegrino,
  Joel Karpiak, Pooja Suresh and Rocco Varela were listed only as rotation
  students.
- **Four alumni listed only under "Staff"** (Cristina Melero, Debbie Jeon,
  Florian Lauck, Shane O'Connor) have the role "Staff".
- **Two wrong emails were corrected:** Lisa Schmidt's page linked to Tobias
  Dorer's address and Yulia Gutierrez's to Dru Myerscough's.
- **Names come from each person's own page** where the old page title
  differed: Jon Zhang, Anum Azam Glasgow, Yang (Sunny) Zhang.
- **9 have no photo:** five early undergraduates and four rotation students.
- **17 older alumni appear on the roster only** (`profile_page: false`).
- Profiles keep `source_url` and `mirror_file`, naming their old Weebly page;
  `build-site.py` uses `mirror_file` to forward old profile addresses.

## Capturing it again

Re-capture the live site into an empty `archive/site/`:

```bash
curl -s https://kortemmelab.ucsf.edu/sitemap.xml | grep -oE '<loc>[^<]+' | sed 's|<loc>http://|https://|' > archive/capture/sitemap-urls.txt
```

```bash
wget --mirror --page-requisites --convert-links --adjust-extension --span-hosts --domains=kortemmelab.ucsf.edu,cdn11.editmysite.com,cdn2.editmysite.com,cdn.mathjax.org --execute robots=off --wait=0.3 --random-wait --tries=3 --timeout=30 --user-agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" --directory-prefix=archive/site --input-file=archive/capture/sitemap-urls.txt --output-file=archive/capture/wget-mirror.log https://kortemmelab.ucsf.edu/
```

wget exits with status 4 because of a few pages missing upstream; that's
expected. Then run the pipeline in order:

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
| `extract.py` | Rebuilds `structure/`; creates any missing `content/` files |
| `alumni-years.py` | Adds `years_in_lab` to alumni files that don't have it |
| `build-bibliography.py` | Creates `content/bibliography.json`; never overwrites it |
| `co-first-authors.py` | Marks co-first authors from the original citations |
| `render-publications.py` | Draws every publication list from the bibliography |

Every script is safe to re-run and uses only the Python standard library.
