---
# A lab member's profile. scripts/add-person.py fills this in from the intake
# form; you can also copy it by hand to content/current-members/<first-last>.md.
# Only `name` is required -- leave anything unknown empty, or delete the line.

# As it should appear on the website.
name: "Jane Q. Doe"
pronouns: ""
# e.g. Graduate Student, Postdoctoral Scholar, Lab Technician.
role: "Graduate Student"
# Graduate program or department, if any.
program: "Biophysics"
# On graduating, set the end year ("2026-2031") and move this file to
# content/alumni/.
years_in_lab: "2026-present"
# Alumni only: what they're doing now.
# current_position: "Assistant Professor, Example University"
# e.g. ["Mike Keiser"]
co_mentors: []
summary: "One to three sentences on what Jane works on."
# Relative to content/. add-person.py copies the headshot here.
photo: "images/people/jane-q-doe.jpg"
# Only if they agreed to show it.
email: ""
# Other links are fine too, e.g. ucsf_profile: "https://profiles.ucsf.edu/..."
links:
  orcid: "https://orcid.org/0000-0002-1825-0097"
  scholar: ""
  website: ""
  github: ""
education:
  - "BS, Chemistry, Example University, 2025"
# DOIs, one per line (arXiv papers too: "10.48550/arxiv.2204.13048"). The
# list on the page is drawn from these by scripts/render-publications.py.
publications:
  - "10.1126/science.abc0881"
---

A longer bio goes here, if there is one. Plain Markdown.
