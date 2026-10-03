#!/usr/bin/env python3
"""Build api.json for the Mix Lab — counts ALWAYS derived from mixlab-manifest.json.

Never hand-edit counts: the manifest is the single authority.
"""
import json
import os
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
BASE = "https://justinahiggins614-cmyk.github.io/signature-ai-mixlab/"


def build(total_seeded=None, forged_through=None):
    import build_manifest
    manifest = build_manifest.build()
    c = manifest["counts"]
    api = {
        "site": manifest["site"],
        "site_id": manifest["site_id"],
        "site_url": BASE,
        "title_status": manifest["title_status"],
        "generated_at": manifest["generated_at"],
        "manifest": BASE + "mixlab-manifest.json",
        "for_bots": ("Deterministic AI hybrid forge. 1,000,000 hybrids "
                     "(JAH-MIX-######), computed on demand from the hybrid "
                     "number. Seeded archive: %d hybrids. "
                     "Deep link: ?mix=JAH-MIX-######" % c["seeded_hybrids"]),
        "counts": {
            "seeded_hybrids": c["seeded_hybrids"],
            "forged_through": c["forged_through"],
            "goal": c["goal"],
            "parent_ais": c["parent_ais"],
            "word_ai_slots": c["word_ai_slots"],
            "word_ai_populated": c["word_ai_populated"],
        },
        "versions": manifest["versions"],
        "parent_pool": manifest["parent_pool"],
        "fictionality": manifest["fictionality"],
        "determinism": manifest["determinism"],
        "endpoints": manifest["endpoints"],
        "sister_sites": manifest["sister_sites"],
    }
    with open(os.path.join(ROOT, "api.json"), "w") as f:
        json.dump(api, f, indent=1)
    print("api.json: %d seeded (from manifest)" % c["seeded_hybrids"])
    return api


if __name__ == "__main__":
    build()
