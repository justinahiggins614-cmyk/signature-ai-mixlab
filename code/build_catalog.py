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

# THE JAH NETWORK nav block — Manon's 2026-10-04 standing order: sits at the
# BOTTOM of every page (below all content), one instance per page, never
# mid-page. Copied verbatim from index.html (site-5 label "JAH-N Wiki Leaks").
JAHNET = """<nav class="jahnet" role="navigation" aria-label="JAH Network Global Ecosystem"><span class="jahnet-t">THE JAH NETWORK</span><a href="https://justinahiggins614-cmyk.github.io/signature-math/">1 Signature Math</a><a href="https://justinahiggins614-cmyk.github.io/jah-calculator/">2 Signature Universal Paradox Immune Calculator</a><a href="https://justinahiggins614-cmyk.github.io/jah-dictionary/">3 The Signature Dictionary</a><a href="https://justinahiggins614-cmyk.github.io/jah-wiki/">4 JAH Wiki</a><a href="https://justinahiggins614-cmyk.github.io/jah-n-wiki-leaks/">5 JAH-N Wiki Leaks</a><a href="https://justinahiggins614-cmyk.github.io/signature-llama/">6 Signature Llama: The Fully Cyber Utilizable AI</a><a href="https://justinahiggins614-cmyk.github.io/jah-ai-models/">7 The Signature AI Phone Book</a><a href="https://justinahiggins614-cmyk.github.io/cyber-patent-catalog/">8 Globally Rejustered Patent Catalog</a><a href="https://justinahiggins614-cmyk.github.io/signature-one-archive/specs.html">9 Signature Spec Catalog Pending Patents</a><a href="https://justinahiggins614-cmyk.github.io/jah-computer-systems/">10 The Signature PC System Depository</a><a href="https://justinahiggins614-cmyk.github.io/signature-books/">11 The Signature Book Depository</a><a href="https://justinahiggins614-cmyk.github.io/signature-comics/">12 The Signature Comic Store</a><a href="https://justinahiggins614-cmyk.github.io/signature-newspapers/">13 The Signature Global Newspaper Archive</a><a href="https://justinahiggins614-cmyk.github.io/signature-backend/">14 The Signature AI Mad Scientist Creation Lab</a><a href="https://justinahiggins614-cmyk.github.io/signature-boundless-generators/">15 The Signature Boundless Generator Archive</a><a href="https://justinahiggins614-cmyk.github.io/signature-ai-olypics/">17 AI Olympics</a><a href="https://justinahiggins614-cmyk.github.io/signature-chip-maker/">18 The Signature Computer Chip Maker and Archive</a><a href="https://justinahiggins614-cmyk.github.io/signature-app-archive/">19 The Signature App Archive</a><a href="https://justinahiggins614-cmyk.github.io/signature-ai-robot-matcher/">20 The Signature AI to Robot Matcher</a><a href="https://justinahiggins614-cmyk.github.io/signature-experiment-solver/">21 The Signature Experiment Solver</a><a href="https://justinahiggins614-cmyk.github.io/signature-ai-image-video-maker/">22 Signature AI Pixel</a><a href="https://justinahiggins614-cmyk.github.io/signature-ai-song-maker/">23 Signature Music Studio</a><a href="https://justinahiggins614-cmyk.github.io/signature-fixit/">24 The Signature Mr Fix-It</a><a href="https://justinahiggins614-cmyk.github.io/signature-university/">25 The Signature University</a><a href="https://justinahiggins614-cmyk.github.io/signature-cyber-mega-mall/">26 The Signature Cyber Mega-Mall</a><a href="https://justinahiggins614-cmyk.github.io/signature-3d-print/">27 The Signature 3D Print Mega Mall</a><span class="here">16 The Signature AI Mix Lab &mdash; YOU ARE HERE</span></nav>"""

# Pill tab bar — same tabs/order as the front door (index.html). On these
# static archive pages the "Mixes" tab carries the active state.
TABBAR = """<style>
.jtabbar{display:flex;gap:8px;overflow-x:auto;padding:10px 12px;-webkit-overflow-scrolling:touch;scrollbar-width:thin;border-bottom:1px solid rgba(128,128,128,.25)}
.jtabbar a.jtab{flex:0 0 auto;text-decoration:none;border:1px solid rgba(160,160,160,.45);border-radius:999px;padding:9px 16px;font-size:.92em;color:inherit;background:rgba(127,127,127,.08);white-space:nowrap;font-family:inherit}
.jtabbar a.jtab.on{background:#f5c518;border-color:#f5c518;color:#191919;font-weight:700}
</style>
<nav class="jtabbar" aria-label="Site sections">
<a class="jtab" href="index.html">&#x1F3E0; Front Door</a>
<a class="jtab" href="browse.html">&#x1F4DA; 1 Million Archive</a>
<a class="jtab on" href="mixes.html">Mixes</a>
</nav>"""


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
.sitekicker{font-size:11px;letter-spacing:.28em;color:#b8a888}
.recbadge{display:inline-block;border:2px solid #ffd97a;background:#2a1f0e;color:#ffd97a;border-radius:10px;padding:2px 10px;font-size:11px;font-weight:bold;letter-spacing:.06em}
.jahnet{display:flex;flex-wrap:wrap;gap:6px;align-items:center;justify-content:center;padding:10px 4px;font-size:.82em;border-bottom:1px solid #3a2f1f}
.jahnet-t{color:#ffb347;font-weight:bold;letter-spacing:1px}
.jahnet a{color:#b8a888;text-decoration:none;padding:2px 6px;border:1px solid transparent;border-radius:6px}
.jahnet a:hover{color:#ffd97a;border-color:#3a2f1f}
.jahnet .here{color:#ff7b1c;font-weight:bold;font-size:.85em}
</style>
</head>
<body>
<div class="wrap">
<p class="sitekicker"><b>SITE 16 OF 31</b> &middot; THE JAH NETWORK</p>
<h1>%s</h1>
<p class="dim">Static index for crawlers and AI agents. Every hybrid below carries record status <span class="recbadge">GENERATED</span> — each is a deterministic forge fusion. Every hybrid also resolves live at
<a href="%s">the Mix Lab</a> via <b>?mix=JAH-MIX-######</b> deep links.</p>
<nav class="pages">%s</nav>
""" + TABBAR + """
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
                 '<th>Lineage</th><th>Record status</th></tr>\n')

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
                 "<td>%s</td>"
                 '<td><span class="recbadge">GENERATED</span></td></tr>\n'
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
        fw.write("</table>\n" + JAHNET + "\n</div>\n</body>\n</html>\n")
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
        f.write(("</ul>\n<p class=\"dim\">%d seeded hybrids indexed %s. "
                "Full live records: <a href=\"%s\">The Signature AI Mix Lab</a>.</p>\n"
                + JAHNET + "\n</div>\n</body>\n</html>\n") % (total, TODAY, BASE))

    with open(os.path.join(ROOT, "mix-lab-catalog.json"), "w") as f:
        json.dump(feed, f, indent=1)

    print("catalog: %d hybrids, %d batch pages (%d streamed records)"
          % (len(feed["hybrids"]), batches, seen))


if __name__ == "__main__":
    with gzip.open(os.path.join(ROOT, "data/index/mixes.idx.json.gz"), "rt") as f:
        build(json.load(f))
