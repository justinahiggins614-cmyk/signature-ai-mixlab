#!/usr/bin/env python3
"""AI Mix Lab canon-coherence check (build-time, fails loudly).

Verifies everything the site presents about an AI matches the phone-book
canon (jah-ai-models/ai-catalog.json) exactly:
  1. data/base-ais.json — every parent AI: id, name, type, description
     match the canon record (description: first-120-chars rule, same as
     JAHtalk.canonIssues in the shared module).
  2. data/wordai-idx.json — shape sanity: [[word, wid], ...], unique ids,
     positive ids.
  3. data/mixes/*.jsonl.gz — every seeded hybrid's parentA/parentB
     id+name resolve to coherent canon parents.

Exit 0 = COHERENT. Any issue -> print and exit 1 (fails loudly).
Run after every drip that touches data/ (drip_mixes.py), before the push.
"""
import gzip, glob, json, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON = os.environ.get("CANON_PATH",
    os.path.expanduser("~/workspace/jah-ai-models/ai-catalog.json"))

issues = []

def fail(msg):
    issues.append(msg)

def norm(x):
    return re.sub(r"\s+", " ", str(x or "")).strip()

def main():
    if not os.path.exists(CANON):
        print("COHERENCE CHECK ABORTED: canon not found at", CANON)
        return 1
    canon = json.load(open(CANON))["records"]
    by_id = {r["ID"]: r for r in canon}

    # ---- 1. base-ais.json vs canon ----
    base = json.load(open(os.path.join(REPO, "data", "base-ais.json")))
    print("base-ais.json: %d parents" % len(base))
    seen = set()
    for b in base:
        bid, bname = b.get("id"), b.get("name")
        if bid in seen:
            fail("duplicate base id %s" % bid)
        seen.add(bid)
        c = by_id.get(bid)
        if c is None:
            fail("base id %s not in phone-book canon" % bid)
            continue
        if bname != c["NAME"]:
            fail("name drift %s: site %r, canon %r" % (bid, bname, c["NAME"]))
        if str(b.get("type", "")).lower() != str(c["TYPE"]).lower():
            fail("type drift %s: site %r, canon %r" % (bid, b.get("type"), c["TYPE"]))
        sd, cd = norm(b.get("desc")), norm(c["DESCRIPTION"])
        if sd[:120] != cd[:120]:
            fail("description drift %s (first 120 chars differ)" % bid)

    # ---- 2. wordai-idx.json sanity ----
    wpath = os.path.join(REPO, "data", "wordai-idx.json")
    w = json.load(open(wpath))
    wids = set()
    for e in w:
        if not (isinstance(e, list) and len(e) == 2 and isinstance(e[0], str) and isinstance(e[1], int)):
            fail("wordai-idx malformed entry: %r" % (e,))
            continue
        if e[1] <= 0:
            fail("wordai-idx non-positive wid: %r" % (e,))
        if e[1] in wids:
            fail("wordai-idx duplicate wid %d" % e[1])
        wids.add(e[1])
    print("wordai-idx.json: %d word AIs" % len(w))

    # ---- 3. seeded hybrid chunks: parents coherent with canon ----
    chunks = sorted(glob.glob(os.path.join(REPO, "data", "mixes", "*.jsonl.gz")))
    nrec = 0
    stamps = set()
    for ch in chunks:
        with gzip.open(ch, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                nrec += 1
                st = r.get("stamp") or ("JAH-MIX-%06d" % r.get("n", 0))
                if st in stamps:
                    fail("duplicate hybrid stamp %s" % st)
                stamps.add(st)
                if not re.fullmatch(r"JAH-MIX-\d{6}", st or ""):
                    fail("bad hybrid stamp %r in %s" % (st, os.path.basename(ch)))
                for pk in ("parentA", "parentB"):
                    p = r.get(pk) or {}
                    pid, pname = p.get("id"), p.get("name")
                    if pid and pid.startswith("JAH-AI-WORD-"):
                        continue  # word-born parents: derived from dictionary, not canon
                    c = by_id.get(pid)
                    if c is None:
                        fail("hybrid %s %s id %s not in canon" % (st, pk, pid))
                    elif pname != c["NAME"]:
                        fail("hybrid %s %s name drift: %r vs canon %r"
                             % (st, pk, pname, c["NAME"]))
    print("mixes chunks: %d seeded hybrids in %d files" % (nrec, len(chunks)))

    if issues:
        print("\nCANON DRIFT DETECTED (%d issues):" % len(issues))
        for i in issues[:40]:
            print("  -", i)
        if len(issues) > 40:
            print("  ... and %d more" % (len(issues) - 40))
        return 1
    print("\nCOHERENCE OK: %d base AIs, %d word AIs, %d seeded hybrids — all canon-coherent." %
          (len(base), len(w), nrec))
    return 0

if __name__ == "__main__":
    sys.exit(main())
