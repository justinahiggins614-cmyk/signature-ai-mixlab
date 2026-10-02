#!/usr/bin/env python3
"""Deterministic hybrid forge engine for the Signature AI Mix Lab.

Same index math as the phone book's Mix Lab AUTO-FORGE (verified: 1,000,000
distinct pairs, i never == j):
    P = 260 base AIs + 100,000 word-AI slots
    z = N-1; i = z % P; q = z // P
    j0 = (q*7919 + i*104729 + 13) % (P-1); j = j0 if j0 < i else j0+1
    v = z % 3   (fusion variant)
Stamps: JAH-MIX-###### (Mix Lab's own stamp line).
"""
import json, re, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

AF_WORDCAP = 100000
AF_MAX = 1000000

def load_base():
    with open(os.path.join(DATA, "base-ais.json")) as f:
        return json.load(f)

def load_wordai():
    with open(os.path.join(DATA, "wordai-idx.json")) as f:
        return json.load(f)  # [[word, wordId], ...]

def pool_size(base):
    return len(base) + AF_WORDCAP

def hybrid_slots(N, base):
    N = max(1, min(AF_MAX, int(N)))
    z = N - 1
    P = pool_size(base)
    i = z % P
    q = z // P
    j0 = (q * 7919 + i * 104729 + 13) % (P - 1)
    j = j0 if j0 < i else j0 + 1
    return {"n": N, "i": i, "j": j, "v": z % 3}

def wordai_display(w):
    if w and w[0].isalpha():
        return w[0].upper() + w[1:]
    return w

def parent_of(slot, base, wordai_by_id):
    if slot < len(base):
        r = base[slot]
        return {"id": r["id"], "name": r["name"], "type": r["type"],
                "desc": r["desc"], "word": "", "unseeded": False}
    wid = slot - len(base) + 1
    word = wordai_by_id.get(wid)
    if word:
        nm = wordai_display(word) + " AI"
        return {"id": "JAH-AI-WORD-%06d" % wid, "name": nm, "type": "word",
                "desc": "A word-born AI: the living mind of the word \"%s\"." % word,
                "word": word, "unseeded": False}
    return {"id": "JAH-AI-WORD-%06d" % wid, "name": "WordAI%d" % wid,
            "type": "word", "desc": "A word AI arriving with the dictionary drip — its file is still being written.",
            "word": "", "unseeded": True}

VARIANTS = [
    "logic leads; the other soul flavors every answer.",
    "soul leads; the other logic steadies every answer.",
    "true 50/50 fusion — neither parent leads, both speak as one.",
]

def blend_name(a, b):
    nm = re.sub(r"[^A-Za-z]", "", a[:4] + b[-4:])
    if len(nm) < 3:
        nm = re.sub(r"[^A-Za-z]", "", a + b)[:8]
    if not nm:
        nm = "Fused"
    return nm[0].upper() + nm[1:]

def first_sentence(m):
    s = str(m or "").split(".")[0].strip()
    return s + "." if s else ""

def make_hybrid(N, base, wordai_by_id):
    h = hybrid_slots(N, base)
    A = parent_of(h["i"], base, wordai_by_id)
    B = parent_of(h["j"], base, wordai_by_id)
    v = h["v"]
    if v == 2:
        lead = VARIANTS[2]
    elif v == 1:
        lead = "%s's %s" % (B["name"], VARIANTS[1].replace("the other", A["name"] + "'s"))
    else:
        lead = "%s's %s" % (A["name"], VARIANTS[0].replace("the other", B["name"] + "'s"))
    mentality = ("Born of %s%s and %s%s %s" % (
        A["name"],
        (" (" + first_sentence(A["desc"]) + ")") if first_sentence(A["desc"]) else "",
        B["name"],
        (" (" + first_sentence(B["desc"]) + ")") if first_sentence(B["desc"]) else "",
        lead))
    abilities = []
    for ab in (A["desc"], B["desc"]):
        s = first_sentence(ab)
        if s:
            abilities.append(s + " — fused")
            if len(abilities) >= 4:
                break
    abilities.append("Hybrid vigor: %s × %s" % (A["name"], B["name"]))
    stamp = "JAH-MIX-%06d" % h["n"]
    name = blend_name(A["name"], B["name"])
    return {
        "n": h["n"], "stamp": stamp, "name": name, "variant": v,
        "parentA": {"id": A["id"], "name": A["name"], "type": A["type"]},
        "parentB": {"id": B["id"], "name": B["name"], "type": B["type"]},
        "mentality": mentality, "abilities": abilities,
        "lineage": "Fused from %s × %s via the deterministic Signature forge v1 (pair %d of 1,000,000)." % (A["id"], B["id"], h["n"]),
        "parents_detail": {"A": A, "B": B},
    }

def slim(rec):
    """Seeded-record form (self-contained, no parents_detail)."""
    return {
        "n": rec["n"], "stamp": rec["stamp"], "name": rec["name"],
        "variant": rec["variant"],
        "parentA": rec["parentA"], "parentB": rec["parentB"],
        "mentality": rec["mentality"], "abilities": rec["abilities"],
        "lineage": rec["lineage"],
        "descA": rec["parents_detail"]["A"]["desc"],
        "descB": rec["parents_detail"]["B"]["desc"],
    }
