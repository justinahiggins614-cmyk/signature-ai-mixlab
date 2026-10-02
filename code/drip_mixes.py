#!/usr/bin/env python3
"""Mix Lab drip: forge the next N hybrids, pack 150/chunk, rebuild index/sitemap/api.

Usage: python3 code/drip_mixes.py --n 1000
Silent-friendly: prints one summary line. Enforces the 800MB repo guard.
"""
import json, gzip, os, sys, argparse, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)
from engine import load_base, load_wordai, make_hybrid, slim

CHUNK = 150
GUARD = 800 * 1024 * 1024

def state_path(): return os.path.join(DATA, "state.json")
def get_state():
    p = state_path()
    if os.path.exists(p):
        return json.load(open(p))
    return {"next_index": 1}

def chunk_name(n):
    return "mixes-c%05d.jsonl.gz" % (((n - 1) // CHUNK) + 1)

def dir_size_bytes(path):
    total = 0
    for dp, _, fns in os.walk(path):
        for fn in fns:
            total += os.path.getsize(os.path.join(dp, fn))
    return total

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    args = ap.parse_args()
    base = load_base()
    wordai = load_wordai()
    wbyid = {wid: w for w, wid in wordai}
    st = get_state()
    start = st["next_index"]
    end = start + args.n  # exclusive
    # generate + pack
    buf = {}
    for N in range(start, end):
        rec = slim(make_hybrid(N, base, wbyid))
        cn = chunk_name(N)
        buf.setdefault(cn, []).append(json.dumps(rec))
    mixes_dir = os.path.join(DATA, "mixes")
    os.makedirs(mixes_dir, exist_ok=True)
    for cn, lines in sorted(buf.items()):
        with gzip.open(os.path.join(mixes_dir, cn), "wt") as f:
            f.write("\n".join(lines) + "\n")
    st["next_index"] = end
    json.dump(st, open(state_path(), "w"))
    # compact index: [n, name, parentA_id, parentB_id, chunk_n]
    idx = []
    for cn in sorted(os.listdir(mixes_dir)):
        if not cn.endswith(".jsonl.gz"):
            continue
        chunk_n = int(cn[7:12])
        with gzip.open(os.path.join(mixes_dir, cn), "rt") as f:
            for line in f:
                r = json.loads(line)
                idx.append([r["n"], r["name"], r["parentA"]["id"], r["parentB"]["id"], chunk_n])
    idx.sort(key=lambda r: r[0])
    os.makedirs(os.path.join(DATA, "index"), exist_ok=True)
    with gzip.open(os.path.join(DATA, "index", "mixes.idx.json.gz"), "wt") as f:
        json.dump(idx, f)
    # sitemap + api
    sys.path.insert(0, HERE)
    import build_sitemap, build_api
    build_sitemap.build(idx)
    build_api.build(len(idx), st["next_index"] - 1)
    size = dir_size_bytes(DATA)
    print("MIXLAB DRIP: +%d hybrids (%d-%d), %d chunks, %d total seeded, data %.1fMB %s" % (
        args.n, start, end - 1, len(buf), len(idx), size / 1048576,
        "GUARD TRIPPED" if size > GUARD else "under guard"))
    if size > GUARD:
        sys.exit(2)

if __name__ == "__main__":
    main()
