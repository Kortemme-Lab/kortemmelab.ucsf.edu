#!/usr/bin/env python3
"""Fix broken links that were broken on the live site too.

Each fix is an exact before/after string, so a fix can never land somewhere
unintended. If a page no longer contains either version -- say, after a fresh
capture of a site someone has since edited -- the script stops and says so
rather than guessing.

Run after tidy-site.py: the strings match its formatting. Idempotent.
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")

FIXES = [
    {
        "page": "lab-alumni.html",
        "why": "Deniz Akpinaroglu's name was split across three links, and "
               "'Deni' and 'z' opened Cody Krivacic's profile",
        "old": '<a href="alumni---cody-krivacic.html">&#8203;Deni</a>'
               '<a href="alumni---cody-krivacic.html">z</a>'
               '<strong><a href="alumni---deniz-akpinaroglu.html">&nbsp;Akpinaroglu, PhD</a></strong>',
        # the same form as every other name on the roster
        "new": '<strong><a href="alumni---deniz-akpinaroglu.html">&#8203;Deniz Akpinaroglu, PhD</a></strong>',
    },
    {
        "page": "current---yulia-gutierrez.html",
        "why": "Yulia's own name linked to current---deniz-akpinaroglu.html, a "
               "page that no longer exists (her profile was evidently copied "
               "from Deniz's); no other profile links the name",
        "old": '<strong><a href="https://kortemmelab.ucsf.edu/current---deniz-akpinaroglu.html">'
               'Yulia Gutierrez</a></strong>',
        "new": '<strong>Yulia Gutierrez</strong>',
    },
]


def main():
    fixed = already = 0
    problems = []
    for fix in FIXES:
        path = os.path.join(SITE, fix["page"])
        text = open(path, encoding="utf-8").read()
        n = text.count(fix["old"])
        if n == 1:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text.replace(fix["old"], fix["new"]))
            print(f"fixed   {fix['page']}: {fix['why']}")
            fixed += 1
        elif n == 0 and fix["new"] in text:
            already += 1
        else:
            problems.append(f"{fix['page']}: expected exactly one match, found {n}")
    print(f"{fixed} fixed, {already} already fixed")
    if problems:
        print("STOPPED -- these pages no longer look as expected:")
        for p in problems:
            print("   ", p)
        sys.exit(1)


if __name__ == "__main__":
    main()
