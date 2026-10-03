#!/usr/bin/env python3
"""Build api.json for the Mix Lab."""
import json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"

def build(total_seeded, forged_through):
    api = {
        "site": "The Signature AI Mix Lab",
        "site_url": BASE,
        "title_status": "provisional — pending Manon's confirmation",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "for_bots": "Deterministic AI hybrid forge. 1,000,000 hybrids (JAH-MIX-######), computed on demand from the hybrid number. Deep link: ?mix=JAH-MIX-######",
        "counts": {
            "seeded_hybrids": total_seeded,
            "forged_through": forged_through,
            "goal": 1000000,
            "parent_ais": 260,
            "word_ai_slots": 100000,
        },
        "endpoints": {
            "hybrid": BASE + "?mix=JAH-MIX-000001",
            "compact_index": BASE + "data/index/mixes.idx.json.gz",
            "chunks": BASE + "data/mixes/mixes-c00001.jsonl.gz",
            "sitemap": BASE + "sitemap.xml",
            "catalog_feed": BASE + "mix-lab-catalog.json",
            "static_index": BASE + "mixes.html",
            "crosslinks_dict": BASE + "data/xlinks/dict-ai-terms.json",
            "crosslinks_wiki": BASE + "data/xlinks/wiki-mix-articles.json",
        },
        "sister_sites": [
            "https://justinahiggins614-cmyk.github.io/jah-ai-models/",
            "https://justinahiggins614-cmyk.github.io/signature-ai-olypics/",
        ],
    }
    with open(os.path.join(ROOT, "api.json"), "w") as f:
        json.dump(api, f, indent=1)
    print("api.json: %d seeded" % total_seeded)

if __name__ == "__main__":
    build(0, 0)
