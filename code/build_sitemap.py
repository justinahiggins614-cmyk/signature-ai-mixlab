#!/usr/bin/env python3
"""Build sitemap.xml (index) + sitemap-mixes-N.xml batch files (?mix= deep links)
for the Mix Lab. Batches of 2500 keep every file small; the index grows as the
forge seeds more hybrids (Site #18 diagnostic fix)."""
import os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"
TODAY = datetime.date.today().isoformat()
BATCH = 2500

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")

def build(idx):
    urls = [BASE + "?mix=JAH-MIX-%06d" % n for n, *_ in idx]
    batches = [urls[i:i + BATCH] for i in range(0, len(urls), BATCH)] or [[]]
    # wipe stale batch files, then rewrite
    for f in os.listdir(ROOT):
        if f.startswith("sitemap-mixes-") and f.endswith(".xml"):
            os.remove(os.path.join(ROOT, f))
    names = []
    for bi, urls_b in enumerate(batches, 1):
        name = "sitemap-mixes-%d.xml" % bi
        names.append(name)
        parts = ['<?xml version="1.0" encoding="UTF-8"?>',
                 '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls_b:
            parts.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(u), TODAY))
        parts.append("</urlset>")
        with open(os.path.join(ROOT, name), "w") as f:
            f.write("\n".join(parts))
    index = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name in names:
        index.append('  <sitemap><loc>%s%s</loc><lastmod>%s</lastmod></sitemap>'
                     % (BASE, name, TODAY))
    index.append('</sitemapindex>')
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write("\n".join(index))
    print("sitemap: %d mix URLs in %d batch files" % (len(urls), len(names)))

if __name__ == "__main__":
    import json, gzip
    with gzip.open(os.path.join(ROOT, "data/index/mixes.idx.json.gz"), "rt") as f:
        build(json.load(f))
