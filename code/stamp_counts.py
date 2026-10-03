#!/usr/bin/env python3
"""Stamp the last-known seeded-hybrid count into index.html's raw HTML.

The <div class="n" id="seededCount"> chip must never boot as a bare "..." —
JS overwrites it live from the manifest on every visit; this is only the
initial content so crawlers and first paint see the real number.
Idempotent: safe to run on every drip.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def stamp():
    manifest = json.load(open(os.path.join(ROOT, "mixlab-manifest.json")))
    count = manifest["counts"]["seeded_hybrids"]
    p = os.path.join(ROOT, "index.html")
    html = open(p).read()
    new = '<div class="n" id="seededCount">%s</div>' % f"{count:,}"
    html2, n = re.subn(r'<div class="n" id="seededCount">.*?</div>', new,
                       html, count=1)
    if n != 1:
        print("stamp_counts: seededCount marker not found", file=sys.stderr)
        return False
    if html2 != html:
        open(p, "w").write(html2)
    print("stamp_counts: seededCount =", f"{count:,}")
    return True


if __name__ == "__main__":
    sys.exit(0 if stamp() else 1)
