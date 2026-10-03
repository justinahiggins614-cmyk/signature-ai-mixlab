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
from engine import load_base, load_wordai, make_hybrid, slim, full_record

CHUNK = 150
GUARD = 800 * 1024 * 1024


def build_index(mixes_dir=None, data_dir=None):
    """Rebuild the compact index from chunks.

    Rows: [n, name, parentA_id, parentB_id, chunk_n, content_hash].
    The content hash is over the canonical full record (ARCHIVED status).
    Readers using r[0..4] are unaffected by the appended hash column.
    """
    from engine import full_record as _fr, load_wordai as _lw
    mixes_dir = mixes_dir or os.path.join(DATA, "mixes")
    data_dir = data_dir or DATA
    wbyid = {wid: w for w, wid in _lw()}
    idx = []
    for cn in sorted(os.listdir(mixes_dir)):
        if not cn.endswith(".jsonl.gz"):
            continue
        chunk_n = int(cn[7:12])
        with gzip.open(os.path.join(mixes_dir, cn), "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                full = _fr(r, status="ARCHIVED", wbyid=wbyid)
                idx.append([r["n"], r["name"], r["parentA"]["id"],
                            r["parentB"]["id"], chunk_n, full["CONTENT-HASH"]])
    idx.sort(key=lambda r: r[0])
    os.makedirs(os.path.join(data_dir, "index"), exist_ok=True)
    with gzip.open(os.path.join(data_dir, "index", "mixes.idx.json.gz"),
                   "wt") as f:
        json.dump(idx, f)
    return idx


def rebuild_derived(idx, checks_passed=None, last_build=None):
    """Rebuild everything derived from the index: sitemap, manifest, api, catalog."""
    import build_sitemap
    import build_manifest
    import build_api
    import build_catalog
    build_sitemap.build(idx)
    manifest = build_manifest.build(checks_passed=checks_passed,
                                    last_build=last_build)
    build_api.build()
    build_catalog.build(idx)
    return manifest


def run_gates():
    """Run all build gates. Returns True iff everything passes."""
    import subprocess
    qa_dir = os.path.join(HERE, "qa")
    gates = [
        [sys.executable, os.path.join(qa_dir, "test_determinism.py")],
        [sys.executable, os.path.join(qa_dir, "check_build.py")],
        [sys.executable, os.path.join(HERE, "coherence_check.py")],
    ]
    ok = True
    for cmd in gates:
        name = os.path.basename(cmd[-1])
        p = subprocess.run(cmd, capture_output=True, text=True)
        print("--- gate %s: %s" % (name, "PASS" if p.returncode == 0 else "FAIL"))
        if p.returncode != 0:
            ok = False
            print(p.stdout[-2000:])
            print(p.stderr[-2000:])
    return ok

def state_path(): return os.path.join(DATA, "state.json")
def get_state():
    p = state_path()
    if os.path.exists(p):
        return json.load(open(p))
    return {"next_index": 1}

def chunk_name(n):
    return "mixes-c%05d.jsonl.gz" % (((n - 1) // CHUNK) + 1)

def write_chunk_merged(mixes_dir, cn, new_lines):
    """Merge new records into a chunk file keyed by record n, sorted.

    NEVER truncate-write: a drip range can start mid-chunk (e.g. --n 1000 is
    not a multiple of CHUNK=150), and a raw 'wt' open would silently wipe the
    records already stored in that chunk. 2026-10-02: this exact bug deleted
    JAH-MIX-003901-004000 and JAH-MIX-004951-005000 across two drips.
    """
    path = os.path.join(mixes_dir, cn)
    merged = {}
    if os.path.exists(path):
        with gzip.open(path, "rt") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                merged[r["n"]] = line
    for line in new_lines:
        r = json.loads(line)
        merged[r["n"]] = line
    with gzip.open(path, "wt") as f:
        for n in sorted(merged):
            f.write(merged[n] + "\n")

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
        write_chunk_merged(mixes_dir, cn, lines)
    st["next_index"] = end
    json.dump(st, open(state_path(), "w"))
    # compact index: [n, name, parentA_id, parentB_id, chunk_n, content_hash]
    idx = build_index()
    # sitemap + manifest + api + catalog feed (never let these go stale)
    rebuild_derived(idx, checks_passed=None)
    # gates on the fresh tree: fail the build (no push) if anything disagrees
    if not run_gates():
        print("MIXLAB DRIP: gates failed — NOT pushing. Fix and re-run.")
        sys.exit(1)
    # stamp the passing run into the manifest + api
    rebuild_derived(idx, checks_passed=True)
    size = dir_size_bytes(DATA)
    print("MIXLAB DRIP: +%d hybrids (%d-%d), %d chunks, %d total seeded, data %.1fMB %s" % (
        args.n, start, end - 1, len(buf), len(idx), size / 1048576,
        "GUARD TRIPPED" if size > GUARD else "under guard"))
    if size > GUARD:
        sys.exit(2)

if __name__ == "__main__":
    main()
