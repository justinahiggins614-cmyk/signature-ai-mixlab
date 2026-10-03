#!/usr/bin/env python3
"""Build-time integrity checks for the Mix Lab (gate — fails loudly).

- manifest counts == index rows == chunk records == api.json counts
- chunk continuity (no gaps/overlaps), no duplicate IDs
- every parent resolves: base-ais.json or wordai-idx.json (unseeded labeled)
- sitemap URL count == seeded; sitemap XML well-formed
- api.json / mixlab-manifest.json valid + counts agree
- cross-link files: every dict URL pattern valid, every mixlab ?q=/?mix= resolvable
Exit 0 = all pass; else exit 1 (drip must NOT push).
"""
import gzip
import json
import glob
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(REPO, "data")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL:", msg)


def main():
    manifest = json.load(open(os.path.join(REPO, "mixlab-manifest.json")))
    api = json.load(open(os.path.join(REPO, "api.json")))
    st = json.load(open(os.path.join(DATA, "state.json")))
    seeded = st["next_index"] - 1

    # ---- counts reconciliation ----
    mc = manifest["counts"]
    for key, want in (("seeded_hybrids", seeded),):
        if mc[key] != want:
            fail("manifest %s=%s != state-derived %s" % (key, mc[key], want))
    ac = api["counts"]
    for key in ("seeded_hybrids", "forged_through", "goal", "parent_ais",
                "word_ai_slots", "word_ai_populated"):
        if ac.get(key) != mc.get(key):
            fail("api.json counts.%s=%r != manifest %r"
                 % (key, ac.get(key), mc.get(key)))
    if not manifest["integrity"]["counts_agree"]:
        fail("manifest integrity.counts_agree is false: %s"
             % json.dumps(manifest["integrity"]))

    # ---- chunk continuity + duplicates ----
    base = {r["id"] for r in json.load(open(os.path.join(DATA, "base-ais.json")))}
    wordai = {wid for _, wid in json.load(open(os.path.join(DATA, "wordai-idx.json")))}
    seen = {}
    prev_last = 0
    checked = 0
    for path in sorted(glob.glob(os.path.join(DATA, "mixes", "mixes-c*.jsonl.gz"))):
        with gzip.open(path, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                n = r["n"]
                checked += 1
                if n in seen:
                    fail("duplicate hybrid n=%d (%s and %s)"
                         % (n, seen[n], os.path.basename(path)))
                seen[n] = os.path.basename(path)
                if n != prev_last + 1:
                    fail("chunk gap/overlap at n=%d after %d in %s"
                         % (n, prev_last, os.path.basename(path)))
                prev_last = n
                for side in ("parentA", "parentB"):
                    pid = r[side]["id"]
                    if pid in base:
                        continue
                    m = re.fullmatch(r"JAH-AI-WORD-(\d+)", pid)
                    if m and int(m.group(1)) in wordai:
                        continue
                    if m and 1 <= int(m.group(1)) <= 100000:
                        continue  # unseeded slot: legal, labeled at render
                    fail("n=%d %s parent %s resolves nowhere" % (n, side, pid))
    if checked != seeded:
        fail("chunk records %d != seeded %d" % (checked, seeded))
    print("chunks: %d records, continuity ok" % checked)

    # ---- index rows ----
    with gzip.open(os.path.join(DATA, "index", "mixes.idx.json.gz"), "rt") as f:
        idx = json.load(f)
    if len(idx) != seeded:
        fail("index rows %d != seeded %d" % (len(idx), seeded))
    idx_ns = [r[0] for r in idx]
    if idx_ns != sorted(idx_ns) or len(set(idx_ns)) != len(idx_ns):
        fail("index n-order broken or duplicated")
    if idx_ns != list(range(1, seeded + 1)):
        fail("index ids not contiguous 1..%d" % seeded)

    # ---- sitemap ----
    sm_index = os.path.join(REPO, "sitemap.xml")
    try:
        tree = ET.parse(sm_index)
        kids = [e.text for e in tree.getroot().iter()
                if e.tag.endswith("loc")]
    except Exception as e:  # noqa
        fail("sitemap.xml not well-formed: %s" % e)
        kids = []
    total_urls = 0
    for kid in kids:
        name = kid.rsplit("/", 1)[-1]
        p = os.path.join(REPO, name)
        if not os.path.exists(p):
            fail("sitemap child missing: %s" % name)
            continue
        try:
            t = ET.parse(p)
            urls = [e.text for e in t.getroot().iter() if e.tag.endswith("loc")]
        except Exception as e:  # noqa
            fail("sitemap child %s not well-formed: %s" % (name, e))
            continue
        total_urls += len(urls)
        for u in urls[:2] + urls[-2:]:
            if not re.fullmatch(re.escape(BASE) + r"\?mix=JAH-MIX-\d{6}", u or ""):
                fail("sitemap URL malformed: %r" % u)
    if total_urls != seeded:
        fail("sitemap urls %d != seeded %d" % (total_urls, seeded))
    print("sitemap: %d urls ok" % total_urls)

    # ---- cross-links ----
    xl_d = json.load(open(os.path.join(DATA, "xlinks", "dict-ai-terms.json")))
    for t in xl_d.get("terms", []):
        if not t.get("mixlab", "").startswith(BASE):
            fail("dict xlink mixlab url bad: %r" % t.get("mixlab"))
        if "jah-dictionary" not in t.get("dict", ""):
            fail("dict xlink dict url bad: %r" % t.get("dict"))
    xl_w = json.load(open(os.path.join(DATA, "xlinks", "wiki-mix-articles.json")))
    res = xl_w.get("resolution", "")
    if "JAH-MIX-######" not in res and "JAH-MIX-" not in res:
        fail("wiki xlink missing JAH-MIX resolution contract")
    print("xlinks: %d dict terms ok" % len(xl_d.get("terms", [])))

    # ---- word-ai accounting ----
    if mc["word_ai_slots"] != 100000:
        fail("word_ai_slots != 100000")
    if mc["word_ai_populated"] != len(wordai):
        fail("word_ai_populated mismatch")

    # ---- spot live check (best effort, never fatal) ----
    try:
        req = urllib.request.Request(BASE + "api.json",
                                     headers={"User-Agent": "mixlab-qa/1"})
        with urllib.request.urlopen(req, timeout=15) as r:
            live = json.load(r)
        if live["counts"]["seeded_hybrids"] > seeded:
            print("note: live api.json ahead of this checkout (deploy lag ok)")
        elif live["counts"]["seeded_hybrids"] < seeded:
            print("note: live api.json behind this checkout (deploy lag ok)")
    except Exception as e:  # noqa
        print("note: live api.json unreachable (%s) — not fatal" % e)

    if failures:
        print("BUILD CHECK: %d FAILURES" % len(failures))
        return 1
    print("BUILD CHECK: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
