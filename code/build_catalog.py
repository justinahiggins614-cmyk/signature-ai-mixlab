#!/usr/bin/env python3
"""Build mix-lab-catalog.json (standardized bot feed) + static HTML fallback
index pages (mixes.html hub + mixes-bN.html batch tables) for the Mix Lab.

Reads data/index/mixes.idx.json.gz + data/mixes/*.jsonl.gz chunks.
Hooked into the 2h drip (drip_mixes.py) so it never goes stale.

Feed note: catalog rows are compact (n, stamp, name, parents, lineage, url).
If seeded totals ever exceed ~50k rows, compact further (drop lineage) to
keep the feed under a few MB; the static batch pages carry full text.
"""
import os
import json
import gzip
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"
BATCH = 2500
TODAY = datetime.date.today().isoformat()
VNAMES = ["Logic-led fusion", "Soul-led fusion", "True 50/50 fusion"]


def hesc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def stream_records():
    """Yield full hybrid records, chunk order, streaming (never all in RAM)."""
    mdir = os.path.join(ROOT, "data", "mixes")
    names = sorted(f for f in os.listdir(mdir) if f.endswith(".jsonl.gz"))
    for nm in names:
        with gzip.open(os.path.join(mdir, nm), "rt") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


PAGE_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s &mdash; The Signature AI Mix Lab</title>
<meta name="description" content="Static index of Signature AI Mix Lab hybrids (JAH-MIX-######) for search engines and AI crawlers.">
<link rel="canonical" href="%s">
<style>
body{background:#14100b;color:#f3e9d2;font-family:Georgia,serif;margin:0;line-height:1.5}
.wrap{max-width:1060px;margin:0 auto;padding:0 14px}
h1{color:#ffd97a} a{color:#ffd97a}
table{width:100%%;border-collapse:collapse;font-size:.9em}
th,td{border:1px solid #3a2f1f;padding:6px 8px;text-align:left;vertical-align:top}
th{color:#ffb347;background:#1e1811}
tr:nth-child(even){background:#181309}
.dim{color:#b8a888}
nav.pages{margin:14px 0;display:flex;gap:8px;flex-wrap:wrap}
</style>
</head>
<body>
<div class="wrap">
<h1>%s</h1>
<p class="dim">Static index for crawlers and AI agents. Every hybrid also resolves live at
<a href="%s">the Mix Lab</a> via <b>?mix=JAH-MIX-######</b> deep links.</p>
<nav class="pages">%s</nav>
"""


def page_nav(batches, cur):
    parts = []
    for b in range(1, batches + 1):
        if b == cur:
            parts.append("<b>JAH-MIX-%06d&ndash;%06d</b>" % ((b - 1) * BATCH + 1, b * BATCH))
        else:
            parts.append('<a href="mixes-b%d.html">JAH-MIX-%06d&ndash;%06d</a>'
                         % (b, (b - 1) * BATCH + 1, b * BATCH))
    return " ".join(parts)


def build(idx):
    idx = sorted(idx, key=lambda r: r[0])
    total = len(idx)
    batches = max(1, (total + BATCH - 1) // BATCH)

    # ---- catalog feed (compact rows) ----
    feed = {
        "site": "The Signature AI Mix Lab",
        "site_url": BASE,
        "title_status": "provisional \u2014 pending Manon's confirmation",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "for_bots": ("Standardized hybrid catalog feed. Each hybrid is a deterministic "
                     "fusion of two parent AIs (JAH-MIX-######). Deep link: ?mix=JAH-MIX-######. "
                     "Full static text lives on the mixes-bN.html batch pages."),
        "counts": {"seeded_hybrids": total, "goal": 1000000,
                   "batch_size": BATCH, "batches": batches},
        "batches": [
            {"batch": b, "from": (b - 1) * BATCH + 1, "to": b * BATCH,
             "static_page": BASE + "mixes-b%d.html" % b,
             "sitemap": BASE + "sitemap-mixes-%d.xml" % b}
            for b in range(1, batches + 1)],
        "hybrids": [],
    }

    # ---- static batch pages (stream records once, bucket by batch) ----
    writers = {}
    for b in range(1, batches + 1):
        path = os.path.join(ROOT, "mixes-b%d.html" % b)
        fw = open(path, "w")
        writers[b] = fw
        title = "Mix Lab hybrids JAH-MIX-%06d\u2013%06d" % ((b - 1) * BATCH + 1, b * BATCH)
        fw.write(PAGE_HEAD % (hesc(title), BASE + "mixes-b%d.html" % b,
                              hesc(title), BASE, page_nav(batches, b)))
        fw.write('<table>\n<tr><th>#</th><th>Hybrid</th><th>Parents</th>'
                 '<th>Lineage</th></tr>\n')

    seen = 0
    for r in stream_records():
        n = r["n"]
        b = (n - 1) // BATCH + 1
        if b > batches:
            continue
        fw = writers[b]
        stamp = r.get("stamp", "JAH-MIX-%06d" % n)
        pA, pB = r.get("parentA", {}), r.get("parentB", {})
        vname = VNAMES[r.get("variant", 0)] if isinstance(r.get("variant"), int) else ""
        fw.write("<tr><td>%d</td>"
                 '<td><a href="?mix=%s">%s</a><br><span class="dim">%s &middot; %s</span></td>'
                 "<td>%s (%s)<br>&times; %s (%s)</td>"
                 "<td>%s</td></tr>\n"
                 % (n, hesc(stamp), hesc(r.get("name", "")),
                    hesc(stamp), hesc(vname),
                    hesc(pA.get("name", "")), hesc(pA.get("id", "")),
                    hesc(pB.get("name", "")), hesc(pB.get("id", "")),
                    hesc(r.get("lineage", ""))))
        feed["hybrids"].append({
            "n": n, "stamp": stamp, "name": r.get("name", ""),
            "variant": vname,
            "parentA": {"id": pA.get("id", ""), "name": pA.get("name", ""),
                       "type": pA.get("type", "")},
            "parentB": {"id": pB.get("id", ""), "name": pB.get("name", ""),
                       "type": pB.get("type", "")},
            "lineage": r.get("lineage", ""),
            "url": BASE + "?mix=" + stamp,
        })
        seen += 1

    for b, fw in writers.items():
        fw.write("</table>\n" + "</div>\n</body>\n</html>\n")
        fw.close()

    # ---- hub page ----
    hub = os.path.join(ROOT, "mixes.html")
    with open(hub, "w") as f:
        f.write(PAGE_HEAD % ("Static hybrid index", BASE + "mixes.html",
                             "Static hybrid index", BASE, page_nav(batches, 0)))
        f.write("<ul>\n")
        for b in range(1, batches + 1):
            f.write('<li><a href="mixes-b%d.html">Batch %d: JAH-MIX-%06d&ndash;%06d</a> '
                    "(%d seeded hybrids)</li>\n"
                    % (b, b, (b - 1) * BATCH + 1, b * BATCH,
                       min(BATCH, total - (b - 1) * BATCH)))
        f.write("</ul>\n<p class=\"dim\">%d seeded hybrids indexed %s. "
                "Full live records: <a href=\"%s\">The Signature AI Mix Lab</a>.</p>\n"
                "</div>\n</body>\n</html>\n" % (total, TODAY, BASE))

    with open(os.path.join(ROOT, "mix-lab-catalog.json"), "w") as f:
        json.dump(feed, f, indent=1)

    print("catalog: %d hybrids, %d batch pages (%d streamed records)"
          % (len(feed["hybrids"]), batches, seen))


if __name__ == "__main__":
    with gzip.open(os.path.join(ROOT, "data/index/mixes.idx.json.gz"), "rt") as f:
        build(json.load(f))
