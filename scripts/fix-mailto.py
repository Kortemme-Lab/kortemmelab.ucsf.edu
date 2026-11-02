#!/usr/bin/env python3
"""Rewrite Cloudflare-obfuscated mail links in the mirror to real mailto: URLs.

On the live site Cloudflare replaces `mailto:x@ucsf.edu` with a link to
/cdn-cgi/l/email-protection#<xor-hex> that its JavaScript un-scrambles in the
browser. In a mirror those links are dead ends, so the addresses are decoded
back to plain mailto: here.

Idempotent: running it again is a no-op.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "archive", "site")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extract import CF_EMAIL_RE, decode_cf_email


def main():
    edited = decoded = 0
    for dirpath, _, filenames in os.walk(SITE):
        for fn in filenames:
            if not fn.lower().endswith((".html", ".htm")):
                continue
            p = os.path.join(dirpath, fn)
            with open(p, encoding="utf-8", errors="surrogateescape") as fh:
                text = fh.read()
            hits = [0]

            def repl(m):
                addr = decode_cf_email(m.group(1))
                if "@" not in addr:
                    return m.group(0)
                hits[0] += 1
                return f"mailto:{addr}"

            new_text = CF_EMAIL_RE.sub(repl, text)
            if new_text != text:
                with open(p, "w", encoding="utf-8", errors="surrogateescape") as fh:
                    fh.write(new_text)
                edited += 1
                decoded += hits[0]
    print(f"decoded {decoded} mail links across {edited} pages")


if __name__ == "__main__":
    main()
