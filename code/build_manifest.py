#!/usr/bin/env python3
"""Build mixlab-manifest.json — the ONE authoritative count/version source.

Every displayed count (homepage, API, archive, search, sitemap) derives from
this manifest. The 2h drip rebuilds it after every run; build gates fail if
any count disagrees with it.
"""
import json
import os
import gzip
import glob
import hashlib
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"
SITE_ID = "SIGNATURE-AI-MIXLAB"

sys_path_guard = True  # noqa


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def chunk_manifest():
    chunks = []
    for path in sorted(glob.glob(os.path.join(DATA, "mixes", "mixes-c*.jsonl.gz"))):
        name = os.path.basename(path)
        n = 0
        first = last = None
        with gzip.open(path, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                n += 1
                if first is None:
                    first = r["n"]
                last = r["n"]
        chunks.append({
            "chunk_id": name.replace(".jsonl.gz", ""),
            "first_n": first,
            "last_n": last,
            "record_count": n,
            "schema_version": "1",
            "sha256": sha256_file(path),
            "generated": datetime.datetime.fromtimestamp(
                os.path.getmtime(path), datetime.timezone.utc).isoformat(),
        })
    return chunks


def build(checks_passed=None, last_build=None):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    st = json.load(open(os.path.join(DATA, "state.json")))
    next_index = st["next_index"]
    seeded = next_index - 1
    chunks = chunk_manifest()
    chunk_total = sum(c["record_count"] for c in chunks)

    idx_path = os.path.join(DATA, "index", "mixes.idx.json.gz")
    with gzip.open(idx_path, "rt") as f:
        idx = json.load(f)
    index_rows = len(idx)
    index_hash = sha256_file(idx_path)

    base = json.load(open(os.path.join(DATA, "base-ais.json")))
    wordai = json.load(open(os.path.join(DATA, "wordai-idx.json")))
    wordai_populated = len({wid for _, wid in wordai})

    # continuity + duplicate audit over chunks
    seen = set()
    dupes = 0
    for path in sorted(glob.glob(os.path.join(DATA, "mixes", "mixes-c*.jsonl.gz"))):
        with gzip.open(path, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                n = json.loads(line)["n"]
                if n in seen:
                    dupes += 1
                seen.add(n)
    missing = [n for n in range(1, seeded + 1) if n not in seen]

    # sitemap batch count
    sitemaps = sorted(f for f in os.listdir(ROOT)
                      if f.startswith("sitemap-mixes-") and f.endswith(".xml"))

    manifest = {
        "manifest_version": "1.0",
        "site_id": SITE_ID,
        "site": "The Signature AI Mix Lab",
        "site_url": BASE,
        "title_status": "provisional \u2014 pending Manon's confirmation",
        "generated_at": now,
        "counts": {
            "seeded_hybrids": seeded,
            "forged_through": seeded,
            "goal": 1000000,
            "parent_ais": len(base),
            "word_ai_slots": 100000,
            "word_ai_populated": wordai_populated,
            "word_ai_pending": 100000 - wordai_populated,
        },
        "versions": {
            "manifest": "1.0",
            "archive": "2026.10.03",
            "generator": "1",
            "record_schema": "1",
            "index": "1",
        },
        "parent_pool": {
            "count": len(base),
            "system": sum(1 for r in base if r["type"] == "system"),
            "persona": sum(1 for r in base if r["type"] == "persona"),
            "domain": sum(1 for r in base if r["type"] == "domain"),
            "snapshot_date": "2026-10-03",
            "canon_source": "jah-ai-models/ai-catalog.json",
            "canon_verified": True,
            "note": ("Generator v1 pool is pinned: new phone-book AIs do NOT "
                     "enter the v1 pool (would break 'same pair, same hybrid'). "
                     "Pending additions (eligible for a future generator v2): "
                     "JAH-AI-DOM-244..253."),
        },
        "index": {
            "rows": index_rows,
            "sha256": index_hash,
            "path": "data/index/mixes.idx.json.gz",
        },
        "chunks": chunks,
        "sitemaps": sitemaps,
        "integrity": {
            "chunk_total": chunk_total,
            "duplicate_ids": dupes,
            "missing_ids": missing[:20],
            "missing_count": len(missing),
            "counts_agree": (seeded == chunk_total == index_rows and dupes == 0
                             and not missing),
        },
        "fictionality": ("Persona parents are fan-style interpretations, not "
                         "affiliated with any rights holder. All hybrid names, "
                         "mentalities, and abilities are original Signature "
                         "creations by Justin Addam Higgins."),
        "determinism": {
            "spec": "mix-determinism/1",
            "spec_doc": "docs/deterministic-spec.md",
            "seed_algorithm": "identity (hybrid number N is the seed)",
            "hash_algorithm": "SHA-256",
            "rule": "Same pair, same hybrid \u2014 forever. Generator v1 pinned.",
        },
        "endpoints": {
            "hybrid": BASE + "?mix=JAH-MIX-000001",
            "manifest": BASE + "mixlab-manifest.json",
            "compact_index": BASE + "data/index/mixes.idx.json.gz",
            "chunks": BASE + "data/mixes/mixes-c00001.jsonl.gz",
            "sitemap": BASE + "sitemap.xml",
            "catalog_feed": BASE + "mix-lab-catalog.json",
            "static_index": BASE + "mixes.html",
            "crosslinks_dict": BASE + "data/xlinks/dict-ai-terms.json",
            "crosslinks_wiki": BASE + "data/xlinks/wiki-mix-articles.json",
            "llms": BASE + "llms.txt",
            "ai_manifest": BASE + "ai-manifest.json",
        },
        "sister_sites": [
            "https://justinahiggins614-cmyk.github.io/jah-ai-models/",
            "https://justinahiggins614-cmyk.github.io/signature-ai-olypics/",
        ],
        "health": {
            "last_build": last_build or now,
            "checks_passed": checks_passed,
            "status": "ok" if checks_passed else "unknown",
        },
    }
    out = os.path.join(ROOT, "mixlab-manifest.json")
    with open(out, "w") as f:
        json.dump(manifest, f, indent=1)
    print("mixlab-manifest.json: %d seeded, integrity=%s" %
          (seeded, manifest["integrity"]["counts_agree"]))
    return manifest


if __name__ == "__main__":
    build()
