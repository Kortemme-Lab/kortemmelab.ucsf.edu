# New lab member form

Set these up in Google Forms or Microsoft Forms (both are available through
UCSF), export the responses as a CSV, and run `scripts/add-person.py` on it.

**Start each question's title with the words in bold below.** The script finds
each answer by how its column title begins, so you can add help text, reorder
questions, or reword the end of a title, but keep the opening words. Anything
not listed here (such as the timestamp, or the address Google records when it
collects emails) is ignored.

| # | Question title (start with the bold words) | Type | Required | Help text for the form |
|---|---|---|---|---|
| 1 | **Full name** (as it should appear on the website) | Short answer | Yes | e.g. "Jane Q. Doe" |
| 2 | **Pronouns** | Short answer | No | Shown on your profile if given. |
| 3 | **Role in the lab** | Multiple choice, with "Other" | Yes | Graduate Student · Postdoctoral Scholar · Research Scientist · Lab Technician · Staff Research Associate · Visiting Scholar · Undergraduate Researcher |
| 4 | **Graduate program or department** | Short answer | No | e.g. "Biophysics", "Bioengineering", "Tetrad". |
| 5 | **Year you joined the lab** | Short answer (number, 2000–2100) | Yes | e.g. 2026 |
| 6 | **Co-mentors** | Short answer | No | If you're co-mentored, who by. Separate names with commas. |
| 7 | **Research summary** (one sentence) | Paragraph | Yes | What you work on, in plain language. Shown under your name. |
| 8 | **Longer bio** | Paragraph | No | Anything else you'd like on your profile. |
| 9 | **Education** | Paragraph | No | One degree per line: "B.S., Chemical Engineering, Northwestern University". Degrees as B.S., B.A., M.S., M.Sc., Ph.D. |
| 10 | **Headshot photo** | File upload (1 file, images only, 10 MB) | No | A clear, recent headshot, at least 400 × 400 pixels. JPG or PNG; iPhone HEIC photos need converting first. |
| 11 | **Lab email address** | Short answer (email) | No | Usually your @ucsf.edu address. |
| 12 | **Show my email on the website** | Multiple choice: Yes / No | Yes | If No, your email isn't stored at all. |
| 13 | **ORCID iD** | Short answer | No | Your 16-digit ORCID, e.g. 0000-0002-1825-0097. Your publications are pulled from it automatically. No ORCID? Leave blank and list DOIs below, or get one free at orcid.org. |
| 14 | **Include publications from before you joined the lab** | Multiple choice: Yes / No | Yes | Yes lists everything from your ORCID; No lists only the DOIs below. |
| 15 | **DOIs of publications** to list (in addition to, or instead of, ORCID) | Paragraph | No | One per line. A DOI ("10.1126/science.abc0881"), a doi.org link, or an arXiv ID ("arXiv:2204.13048"). Use this for anything missing from ORCID, like a brand-new preprint. |
| 16 | **Google Scholar profile** | Short answer (URL) | No | |
| 17 | **Personal website** | Short answer (URL) | No | |
| 18 | **GitHub** | Short answer | No | Your username or profile link. |

## Setting up the photo question

File-upload questions save each photo to the form owner's cloud storage, not
into the CSV (the CSV only gets a link). So after exporting the responses:

- **Google Forms:** in the Responses tab, open the uploads folder in Google
  Drive and download it. Respondents need a Google account to upload; anyone
  without one can email you their photo instead.
- **Microsoft Forms:** uploads land in a OneDrive or SharePoint folder named
  after the form; download it. Respondents need a UCSF account.

Put the downloaded photos in `intake/photos/`. The script matches each photo to
its person by name: Google names uploads "*original name* - *Respondent
name*.jpg", which is enough. If a name doesn't match, pass the photo
explicitly with `--photo`.

## Privacy

The exported CSV holds email addresses and other personal details. Keep it
out of the public repository: `intake/.gitignore` already excludes
`intake/*.csv` (other than the example) and the contents of `intake/photos/`.
Email addresses are only written to a profile when someone answers Yes to
question 12.
