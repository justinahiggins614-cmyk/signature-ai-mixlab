#!/usr/bin/env python3
"""Build sitemap.xml (index) + sitemap-mixes-1.xml (?mix= deep links) for the Mix Lab."""
import os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"
TODAY = datetime.date.today().isoformat()

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;")

def build(idx):
    urls = [BASE + "?mix=JAH-MIX-%06d" % n for n, *_ in idx]
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        parts.append("  <url><loc>%s</loc><lastmod>%s</lastmod></url>" % (esc(u), TODAY))
    parts.append("</urlset>")
    with open(os.path.join(ROOT, "sitemap-mixes-1.xml"), "w") as f:
        f.write("\n".join(parts))
    index = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
             '  <sitemap><loc>%ssitemap-mixes-1.xml</loc><lastmod>%s</lastmod></sitemap>\n'
             '</sitemapindex>') % (BASE, TODAY)
    with open(os.path.join(ROOT, "sitemap.xml"), "w") as f:
        f.write(index)
    print("sitemap: %d mix URLs" % len(urls))

if __name__ == "__main__":
    import json, gzip
    with gzip.open(os.path.join(ROOT, "data/index/mixes.idx.json.gz"), "rt") as f:
        build(json.load(f))
