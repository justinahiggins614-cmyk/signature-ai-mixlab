#!/usr/bin/env python3
"""Determinism regression suite for the Mix Lab (build gate — fails loudly).

1. Python engine (code/engine.py) vs frozen test_vectors.json:
   same N -> same parents, name, variant, seed, content hash.
2. JS mirror (index.html engine block) vs Python engine via node:
   same N -> same stamp, name, parents, seed. Catches mirror drift.
3. Repeatability: make_hybrid(N) twice -> identical output.

Exit 0 = all pass. Any failure -> exit 1 (drip must NOT push).
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "code"))
from engine import (make_hybrid, full_record, formal_seed, load_base,
                    load_wordai, GENERATOR_VERSION)

failures = []


def fail(msg):
    failures.append(msg)
    print("FAIL:", msg)


def main():
    vectors = json.load(open(os.path.join(HERE, "test_vectors.json")))
    base = load_base()
    wbyid = {wid: w for w, wid in load_wordai()}

    # ---- 1. Python engine vs frozen vectors ----
    for ns, v in sorted(vectors.items(), key=lambda kv: int(kv[0])):
        N = int(ns)
        r = make_hybrid(N, base, wbyid)
        rec = dict(r)
        rec["descA"] = r["parents_detail"]["A"]["desc"]
        rec["descB"] = r["parents_detail"]["B"]["desc"]
        f = full_record(rec, wbyid=wbyid)
        for key, got, want in (
                ("stamp", r["stamp"], v["stamp"]),
                ("name", r["name"], v["name"]),
                ("variant", r["variant"], v["variant"]),
                ("parentA", r["parentA"]["id"], v["parentA_id"]),
                ("parentB", r["parentB"]["id"], v["parentB_id"]),
                ("seed", formal_seed(N, r["variant"]), v["seed"]),
                ("content_hash", f["CONTENT-HASH"], v["content_hash"]),
                ("generator", GENERATOR_VERSION, v["generator_version"])):
            if got != want:
                fail("N=%d vector mismatch %s: got %r want %r"
                     % (N, key, got, want))
        # repeatability
        r2 = make_hybrid(N, base, wbyid)
        if json.dumps(r, sort_keys=True) != json.dumps(r2, sort_keys=True):
            fail("N=%d not repeatable" % N)
    print("python-engine vectors: %d checked" % len(vectors))

    # ---- 2. JS mirror parity via node ----
    html = open(os.path.join(REPO, "index.html")).read()
    m = re.search(
        r"/\* =+ deterministic forge engine.*?\*/(.*?)/\* =+ record resolution",
        html, re.S)
    if not m:
        fail("could not extract JS engine block from index.html")
    else:
        js_engine = m.group(1)
        node_src = (
            js_engine + "\n"
            "BASE=" + json.dumps(
                [{"id": r["id"], "name": r["name"], "type": r["type"],
                  "desc": r["desc"]} for r in base]) + ";\n"
            "WORDAIMAP={};\n"
            + json.dumps([[w, wid] for w, wid in load_wordai()]) +
            ".forEach(function(e){WORDAIMAP[e[1]]=e[0]});\n"
            + "var out={};\n"
            + json.dumps([int(n) for n in vectors]) +
            ".forEach(function(N){var h=makeHybrid(N);"
            "out[N]={stamp:h.stamp,name:h.name,variant:h.variant,"
            "a:h.parentA.id,b:h.parentB.id,"
            "seed:\"MIX-\"+String(N).padStart(6,\"0\")+\"-V\"+h.variant+\"-FORGE1\"}});\n"
            "console.log(JSON.stringify(out));\n")
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False) as tf:
            tf.write(node_src)
            tf_path = tf.name
        try:
            p = subprocess.run(["node", tf_path], capture_output=True,
                               text=True, timeout=60)
        finally:
            os.unlink(tf_path)
        if p.returncode != 0:
            fail("node JS-mirror run failed: " + p.stderr[:300])
        else:
            js_out = json.loads(p.stdout)
            for ns, v in vectors.items():
                j = js_out[ns]
                for key, jk, want in (
                        ("stamp", "stamp", v["stamp"]),
                        ("name", "name", v["name"]),
                        ("variant", "variant", v["variant"]),
                        ("parentA", "a", v["parentA_id"]),
                        ("parentB", "b", v["parentB_id"]),
                        ("seed", "seed", v["seed"])):
                    if j[jk] != want:
                        fail("JS mirror N=%s %s: got %r want %r"
                             % (ns, key, j[jk], want))
            print("js-mirror parity: %d vectors checked" % len(vectors))

    # ---- 3. boundary + invalid handling ----
    for bad in (0, -5, 1000001):
        try:
            r = make_hybrid(bad, base, wbyid)
            if not (1 <= r["n"] <= 1000000):
                fail("N=%r not clamped to 1..1000000" % bad)
        except Exception as e:  # noqa - clamping is also acceptable
            fail("N=%r raised %r" % (bad, e))

    if failures:
        print("DETERMINISM: %d FAILURES" % len(failures))
        return 1
    print("DETERMINISM: ALL PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
